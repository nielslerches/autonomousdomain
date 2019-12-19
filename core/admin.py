from django.contrib import admin
from django.db.models import Model

from core import models, forms


for model in [
    model
    for model in Model.__subclasses__()
    if model.__module__ == "core.models" and not model in [models.Barcode,]
]:
    admin.site.register(
        model, type(model.__class__.__name__ + "Admin", (admin.ModelAdmin,), {}),
    )


class BarcodeAdmin(admin.ModelAdmin):
    form = forms.BarcodeForm


admin.site.register(models.Barcode, BarcodeAdmin)
