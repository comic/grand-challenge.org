from django.db import models
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm

from grandchallenge.subdomains.utils import reverse


class PaymentStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    REQUESTED = "REQUESTED", "Invoice Requested"
    ISSUED = "ISSUED", "Invoice Issued"
    PAID = "PAID", "Paid"


class PaymentTypeChoices(models.TextChoices):
    COMPLIMENTARY = "COMPLIMENTARY", "Complimentary"
    PREPAID = "PREPAID", "Prepaid"
    POSTPAID = "POSTPAID", "Postpaid"


class Invoice(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    issued_on = models.DateField(
        help_text="The date when the invoice was issued", blank=True, null=True
    )
    paid_on = models.DateField(
        help_text="The date when the invoice was paid", blank=True, null=True
    )
    last_checked_on = models.DateField(
        help_text="The date when the invoice status was last checked",
        blank=True,
        null=True,
    )

    challenge = models.ForeignKey(
        to="challenges.Challenge",
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    support_costs_euros = models.PositiveIntegerField(
        help_text="The support contribution in Euros"
    )
    compute_costs_euros = models.PositiveIntegerField(
        help_text="The capacity reservation in Euros"
    )
    storage_costs_euros = models.PositiveIntegerField(
        help_text="The storage costs in Euros"
    )

    internal_invoice_number = models.CharField(
        max_length=16, help_text="The internal invoice number", blank=True
    )
    internal_client_number = models.CharField(
        max_length=8, help_text="The internal client number", blank=True
    )
    internal_comments = models.TextField(
        help_text="Internal comments about the invoice", blank=True
    )

    contact_name = models.CharField(
        max_length=32,
        help_text="Name of the person the invoice should be sent to",
        blank=True,
    )
    contact_email = models.EmailField(
        help_text="Email of the person the invoice should be sent to",
        blank=True,
    )
    billing_address = models.TextField(
        help_text="The physical address of the client", blank=True
    )
    vat_number = models.CharField(
        max_length=32, help_text="The VAT number of the client", blank=True
    )
    external_reference = models.TextField(
        help_text="Optional reference to be included with the invoice for the client",
        blank=True,
    )

    PaymentTypeChoices = PaymentTypeChoices
    payment_type = models.CharField(
        max_length=13,
        choices=PaymentTypeChoices.choices,
        default=PaymentTypeChoices.PREPAID,
    )
    PaymentStatusChoices = PaymentStatusChoices
    payment_status = models.CharField(
        max_length=11,
        choices=PaymentStatusChoices.choices,
        default=PaymentStatusChoices.INITIALIZED,
    )

    @property
    def total_amount_euros(self):
        try:
            return (
                self.support_costs_euros
                + self.compute_costs_euros
                + self.storage_costs_euros
            )
        except TypeError:
            return

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(payment_type__in=PaymentTypeChoices.values),
                name="payment_type_in_choices",
            ),
            models.CheckConstraint(
                check=models.Q(payment_status__in=PaymentStatusChoices.values),
                name="payment_status_in_choices",
            ),
        ]

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        assign_perm(
            f"view_{self._meta.model_name}",
            self.challenge.admins_group,
            self,
        )


class InvoiceUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        raise RuntimeError(
            "User permissions should not be assigned for this model"
        )


class InvoiceGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)

    def get_absolute_url(self):
        return reverse(
            "invoices:detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "pk": self.pk,
            },
        )
