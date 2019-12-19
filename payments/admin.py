from django.contrib import admin

from payments import models


class SalesChannelPaymentServiceAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.SalesChannelPaymentService, SalesChannelPaymentServiceAdmin)
