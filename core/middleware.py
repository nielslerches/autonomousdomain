import json

from django.http.request import HttpRequest
from django.utils.deprecation import MiddlewareMixin


class JsonBodyMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.method in ("POST", "PUT") and request.content_type.startswith(
            "application/json"
        ):
            setattr(request, "POST", json.loads(request.body))
