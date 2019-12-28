from functools import reduce

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

import barcode
import pycountry

from . import managers


class Warehouse(models.Model):
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class DeliveryCenter(models.Model):
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class FulfillmentCenter(models.Model):
    warehouse = models.OneToOneField(
        Warehouse, on_delete=models.PROTECT, related_name="fulfillment_center"
    )
    delivery_center = models.OneToOneField(
        DeliveryCenter, on_delete=models.PROTECT, related_name="fulfillment_center"
    )
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Market(models.Model):
    COUNTRY = "country"
    SALES_CHANNEL = "sales channel"

    TYPES = ((COUNTRY, COUNTRY), (SALES_CHANNEL, SALES_CHANNEL))

    type = models.CharField(max_length=255, choices=TYPES, default=COUNTRY)
    identifier = models.CharField(max_length=255)

    def __str__(self):
        if self.type == self.COUNTRY:
            return pycountry.countries.get(alpha_3=self.identifier).name
        elif self.type == self.SALES_CHANNEL:
            return str(SalesChannel.objects.get(pk=self.identifier))
        raise NotImplementedError(self.type)


class OnlineShop(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


def OR(a, b):
    return a | b


class SalesChannel(models.Model):
    name = models.CharField(max_length=255, blank=True)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=reduce(
            OR,
            [
                Q(app_label=model._meta.app_label, model=model._meta.model_name)
                for model in [OnlineShop,]
            ],
        ),
        null=True,
    )
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey()

    def __str__(self):
        return self.name or self.content_object.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="core_saleschannel_content_type_object_id_uniq",
            ),
        ]


class Supplier(models.Model):
    name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class SupplierFulfillmentCenter(models.Model):
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="fulfillment_centers"
    )
    fulfillment_center = models.ForeignKey(
        FulfillmentCenter, on_delete=models.PROTECT, related_name="suppliers"
    )

    def __str__(self):
        return str(self.supplier) + " <- " + str(self.fulfillment_center)


class SupplierFulfillmentCenterSalesChannel(models.Model):
    supplier_fulfillment_center = models.ForeignKey(
        SupplierFulfillmentCenter,
        on_delete=models.PROTECT,
        related_name="sales_channels",
    )
    sales_channel = models.ForeignKey(
        SalesChannel,
        on_delete=models.PROTECT,
        related_name="supplier_fulfillment_centers",
    )

    def __str__(self):
        return str(self.sales_channel) + " <- " + str(self.supplier_fulfillment_center)


class SupplierFulfillmentCenterSalesChannelMarket(models.Model):
    supplier_fulfillment_center_sales_channel = models.ForeignKey(
        SupplierFulfillmentCenterSalesChannel,
        on_delete=models.PROTECT,
        related_name="markets",
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.PROTECT,
        related_name="supplier_fulfillment_center_sales_channels",
    )

    def __str__(self):
        return (
            str(self.market)
            + " <- "
            + str(self.supplier_fulfillment_center_sales_channel)
        )


class Barcode(models.Model):
    TYPES = tuple(zip(barcode.PROVIDED_BARCODES, barcode.PROVIDED_BARCODES))

    barcode = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=TYPES, default="ean13")

    objects = managers.BarcodeManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["barcode", "type"], name="core_barcode_barcode_type_unique",
            ),
        ]

    def __str__(self):
        return "{} ({})".format(self.barcode, self.get_type_display(),)


class FulfillmentCenterArticle(models.Model):
    fulfillment_center = models.ForeignKey(FulfillmentCenter, on_delete=models.PROTECT)
    article_number = models.CharField(max_length=255)
    barcodes = models.ManyToManyField(
        Barcode, related_name="fulfillment_center_barcodes"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fulfillment_center", "article_number"],
                name="core_fulfillmentcenterarticle_fulfillment_center_article_number_unique",
            )
        ]

    def __str__(self):
        return "{} ({})".format(self.article_number, self.fulfillment_center)


class SalesChannelSupplierArticle(models.Model):
    sales_channel = models.ForeignKey(SalesChannel, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    article_number = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    price_old = models.DecimalField(max_digits=9, decimal_places=2)

    objects = managers.SalesChannelSupplierArticleManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sales_channel", "supplier", "article_number"],
                name="core_saleschannelsupplierarticle_sales_channel_supplier_article_unique",
            ),
        ]

    def __str__(self):
        return "{} ({}, {})".format(
            self.article_number, self.sales_channel, self.supplier,
        )
