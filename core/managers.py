from django.db import models


class BarcodeManager(models.Manager):
    def get_by_natural_key(self, barcode, type):
        return self.get(barcode=barcode, type=type)


class SalesChannelSupplierArticleManager(models.Model):
    def get_by_natural_key(self, sales_channel, supplier, article_number):
        return self.get(
            sales_channel=sales_channel,
            supplier=supplier,
            article_number=article_number,
        )
