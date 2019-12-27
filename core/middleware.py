import json

from django.utils.deprecation import MiddlewareMixin
from django.http.request import HttpRequest


class JsonBodyMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.method in ("POST", "PUT") and request.content_type.startswith(
            "application/json"
        ):
            setattr(request, request.method, json.loads(request.body))
