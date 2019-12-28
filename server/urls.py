"""server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
import signal

from django.conf import settings
from django.http import HttpResponse
from django.urls import path

from core.models import Warehouse
from core.views import create_resource


def kill(request):
    os.kill(os.getpid(), signal.SIGKILL)


app_name = "server"

urlpatterns = [
    path("health/", lambda request: HttpResponse("OK"), name="health"),
    path("kill/", kill, name="kill"),
]

if settings.SERVER_OBJECT_TYPE:
    urlpatterns += create_resource(app_name=app_name, model=Warehouse, fields=["name"])
