from django.db import models
from django.db.models import Q
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase
from guardian.shortcuts import assign_perm


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

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(payment_type__in=PaymentTypeChoices.values),
                name="payment_type_in_choices",
            ),
            models.CheckConstraint(
                check=Q(payment_status__in=PaymentStatusChoices.values),
                name="payment_status_in_choices",
            ),
            models.CheckConstraint(
                name="issued_on_date_required_for_issued_payment_status",
                check=Q(issued_on__isnull=False)
                | ~Q(payment_status=PaymentStatusChoices.ISSUED)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must set the 'Issued on' date.",
            ),
            models.CheckConstraint(
                name="paid_on_date_required_for_paid_payment_status",
                check=Q(paid_on__isnull=False)
                | ~Q(payment_status=PaymentStatusChoices.PAID)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Paid',"
                " you must set the 'Paid on' date.",
            ),
            models.CheckConstraint(
                name="comments_required_for_complimentary_payment_type",
                check=Q(internal_comments__gt="")
                | ~Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="Please explain why the invoice is "
                "complimentary in the internal comments.",
            ),
            models.CheckConstraint(
                name="contact_name_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | Q(contact_name__gt=""),
                violation_error_message="Contact name is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="contact_email_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | Q(contact_email__gt=""),
                violation_error_message="Contact email is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="billing_address_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | Q(billing_address__gt=""),
                violation_error_message="Billing address is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="vat_number_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | Q(vat_number__gt=""),
                violation_error_message="VAT number is required for non-complimentary invoices.",
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
