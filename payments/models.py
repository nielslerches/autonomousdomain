from django.db import models


class SalesChannelPaymentService(models.Model):
    GIFTCARD = "giftcard"

    PAYMENT_SERVICES = ((GIFTCARD, GIFTCARD),)

    name = models.CharField(max_length=255)
    sales_channel = models.ForeignKey("core.SalesChannel", on_delete=models.PROTECT)
    payment_service = models.CharField(max_length=255, choices=PAYMENT_SERVICES)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sales_channel", "payment_service"],
                name="payments_saleschannelpaymentservice_sales_channel_payment_service_unique",
            ),
        ]


class Transaction(models.Model):
    PENDING_AUTHORIZATION = "pending authorization"
    AUTHORIZED = "authorized"

    PENDING_CAPTURE = "pending capture"
    CAPTURED = "captured"

    PENDING_CANCELLATION = "pending cancellation"
    CANCELLED = "cancelled"

    STATUSES = (
        (PENDING_AUTHORIZATION, PENDING_AUTHORIZATION),
        (AUTHORIZED, AUTHORIZED),
        (PENDING_CAPTURE, PENDING_CAPTURE),
        (CAPTURED, CAPTURED),
        (PENDING_CANCELLATION, PENDING_CANCELLATION),
        (CANCELLED, CANCELLED),
    )

    status = models.CharField(max_length=255, choices=STATUSES)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    currency = models.CharField(max_length=255)
