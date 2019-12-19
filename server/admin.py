from django.conf import settings
from django.contrib import admin

from server.models import Server


class ServerAdmin(admin.ModelAdmin):
    readonly_fields = ("last_known_status",)


if not settings.SERVER_OBJECT_TYPE:
    admin.site.register(Server, ServerAdmin)
