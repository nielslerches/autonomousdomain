from typing import Type

from django import forms
from django.http.response import JsonResponse
from django.db import models
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.urls import reverse_lazy, path


def swallow(exceptions, default, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if type(e) in exceptions:
            return default
        raise e


def get_fields(model: Type[models.Model]):
    return {field.name: field for field in model._meta.get_fields()}


def is_chain_of_foreign_objects(model: Type[models.Model], split_key: list):
    fields = get_fields(model)

    for path in split_key:
        field = fields[path]
        if not any((field.one_to_many, field.one_to_one)):
            break
        model = fields[path].related_model
        fields = get_fields(model)
    else:
        return True

    return False


def get_queryset_operations(model, request_data):
    queryset_operations = {
        "select_related": [],
        "prefetch_related": [],
        "filter": [],
        "values": [],
    }

    for key in request_data:
        split_key = key.split(".")
        value = request_data[key]

        for depth, path in enumerate(split_key):
            pred_paths = split_key[: depth + 1]

            if is_chain_of_foreign_objects(model, pred_paths):
                queryset_operations["select_related"].append("__".join(pred_paths))

        # TODO: Implement prefetch_related

        queryset_operations["filter"].append(
            models.Q(**{key.replace(".", "__"): value})
        )

        # TODO: Implement values

    return queryset_operations


def serialize_model_instance(model_instance, show_fields=None):
    if model_instance is None:
        return None

    if show_fields is None:
        show_fields = []

    model = type(model_instance)
    fields = [
        field
        for field in model._meta.get_fields()
        if any(
            [
                ((show_field == field.name) or show_field.startswith(field.name + "."))
                for show_field in show_fields
            ]
        )
        and field.name != "password"
    ]
    own_fields = [
        field for field in fields if getattr(field, "related_model", None) is None
    ]
    direct_fields = [
        field
        for field in fields
        if any((field.one_to_many, field.one_to_one))
        and not getattr(field, "multiple", False)
    ]
    many_fields = [
        field for field in fields if any((field.many_to_many, field.many_to_one))
    ]

    serialized_model_instance = {
        field.name: getattr(model_instance, field.name) for field in own_fields
    }

    serialized_model_instance.update(
        {
            field.name: serialize_model_instance(
                model_instance=swallow(
                    [
                        getattr(
                            model, getattr(field, "related_name", field.name)
                        ).RelatedObjectDoesNotExist
                    ],
                    None,
                    getattr,
                    model_instance,
                    getattr(field, "related_name", field.name),
                ),
                show_fields=[
                    show_field.split(".", 1)[-1]
                    for show_field in show_fields
                    if show_field.startswith(
                        getattr(field, "related_name", field.name) + "."
                    )
                ],
            )
            for field in direct_fields
        }
    )

    serialized_model_instance.update(
        {
            field.name: [
                serialize_model_instance(
                    model_instance=foreign_object,
                    show_fields=[
                        show_field.split(".", 1)[-1]
                        for show_field in show_fields
                        if show_field.startswith(field.name + ".")
                    ],
                )
                for foreign_object in getattr(model_instance, field.name).all()
            ]
            for field in many_fields
        }
    )

    return serialized_model_instance


class RESTFulObjectView(UpdateView, DetailView):
    response_class = JsonResponse
    model: Type[models.Model] = None
    app_name: str = None

    def render_to_response(self, context, **response_kwargs):
        return self.response_class(
            {
                "data": serialize_model_instance(
                    self.object,
                    show_fields=self.request.GET.getlist("fields") or self.fields,
                ),
                "error": None,
            }
        )

    def get_success_url(self):
        return reverse_lazy(
            self.app_name + ":" + self.model._meta.verbose_name.replace(" ", "_"),
            args=(self.object.id,),
        )

    def form_valid(self, form: forms.ModelForm):
        return self.response_class({"data": "OK", "error": None})

    def form_invalid(self, form: forms.ModelForm):
        return self.response_class({"data": "NOT OK", "error": form.errors})


class RESTFulListView(CreateView, ListView):
    response_class = JsonResponse
    model: Type[models.Model] = None
    app_name: str = None

    def get_queryset_operations(self, request_data):
        return get_queryset_operations(self.model, request_data)

    def get_queryset(self):
        queryset_operations = self.get_queryset_operations(
            {
                key: value
                for key, value in self.request.GET.items()
                if key not in ("fields",)
            }
        )
        queryset = self.model.objects

        if queryset_operations["select_related"]:
            queryset.select_related(*queryset_operations["select_related"])

        if queryset_operations["prefetch_related"]:
            queryset.prefetch_related(*queryset_operations["prefetch_related"])

        for condition in queryset_operations["filter"]:
            queryset = queryset.filter(condition)

        queryset = (
            queryset.all()
            if queryset_operations["prefetch_related"]
            else queryset.iterator()
        )

        object_list = [
            serialize_model_instance(
                model_instance,
                show_fields=self.request.GET.getlist("fields") or self.fields,
            )
            for model_instance in queryset
        ]

        return object_list

    def render_to_response(self, context, **response_kwargs):
        return self.response_class(
            {"data": context["object_list"], "error": None}, **response_kwargs
        )

    def get_success_url(self, instance=None):
        return reverse_lazy(
            self.app_name + ":" + self.model._meta.verbose_name.replace(" ", "_"),
            args=(self.object.id if instance is None else instance.id,),
        )

    def form_valid(self, form: forms.ModelForm):
        self.object = form.save()

        response = self.response_class({"data": "OK", "error": None})
        response["Location"] = self.get_success_url(instance=form.instance)
        return response

    def form_invalid(self, form: forms.ModelForm):
        return self.response_class({"data": "NOT OK", "error": form.errors})


def create_resource(app_name, model, fields):
    name_plural = model._meta.verbose_name_plural.replace(" ", "_")
    name = model._meta.verbose_name.replace(" ", "_")

    return [
        path(
            "{}/".format(name_plural),
            RESTFulListView.as_view(app_name=app_name, model=model, fields=fields),
            name=name_plural,
        ),
        path(
            "{}/<int:pk>/".format(name_plural),
            RESTFulObjectView.as_view(app_name=app_name, model=model, fields=fields),
            name=name,
        ),
    ]
