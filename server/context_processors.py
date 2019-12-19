from django.http import HttpRequest

from server.models import get_server_object


def server(request: HttpRequest) -> dict:
    server_obj = get_server_object()

    return {
        "server_obj": server_obj,
    }
