from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, ExpressionWrapper, F, Q
from django.db.models.functions import Cast
from django.db.transaction import on_commit
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import FieldChangeMixin
from grandchallenge.invoices.tasks import (
    send_challenge_invoice_issued_notification_emails,
)


class PaymentStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", "Initialized"
    REQUESTED = "REQUESTED", "Invoice Requested"
    ISSUED = "ISSUED", "Invoice Issued"
    PAID = "PAID", "Paid"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentTypeChoices(models.TextChoices):
    COMPLIMENTARY = "COMPLIMENTARY", "Complimentary"
    PREPAID = "PREPAID", "Prepaid"
    POSTPAID = "POSTPAID", "Postpaid"


class InvoiceQuerySet(models.QuerySet):
    def with_due_date(self):
        return self.annotate(
            due_date=Cast(
                F("issued_on") + settings.CHALLENGE_INVOICE_OVERDUE_CUTOFF,
                output_field=models.DateField(),
            ),
        )

    def with_overdue_status(self):
        today = now().date()

        return self.with_due_date().annotate(
            is_overdue=ExpressionWrapper(
                Q(
                    payment_type__in=[
                        Invoice.PaymentTypeChoices.PREPAID,
                        Invoice.PaymentTypeChoices.POSTPAID,
                    ],
                    payment_status=Invoice.PaymentStatusChoices.ISSUED,
                    due_date__lt=today,
                ),
                output_field=models.BooleanField(),
            ),
            is_due=ExpressionWrapper(
                Q(
                    payment_type__in=[
                        Invoice.PaymentTypeChoices.PREPAID,
                        Invoice.PaymentTypeChoices.POSTPAID,
                    ],
                    payment_status=Invoice.PaymentStatusChoices.ISSUED,
                    due_date__gte=today,
                    issued_on__lte=today,
                ),
                output_field=models.BooleanField(),
            ),
        )

    @property
    def status_aggregates(self):
        return self.aggregate(
            num_is_overdue=Count(
                "is_overdue", filter=Q(is_overdue=True), distinct=True
            ),
            num_is_due=Count("is_due", filter=Q(is_due=True), distinct=True),
        )


class Invoice(FieldChangeMixin, models.Model):
    objects = InvoiceQuerySet.as_manager()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    issued_on = models.DateField(
        help_text="The date when the invoice was issued (required for issued invoices)",
        blank=True,
        null=True,
    )
    paid_on = models.DateField(
        help_text="The date when the invoice was paid (required for paid invoices)",
        blank=True,
        null=True,
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
        max_length=16,
        help_text="The internal invoice number (required for issued invoices)",
        blank=True,
    )
    internal_client_number = models.CharField(
        max_length=8,
        help_text="The internal client number (required for issued invoices)",
        blank=True,
    )
    internal_comments = models.TextField(
        help_text="Internal comments about the invoice (required for complimentary invoices)",
        blank=True,
    )

    contact_name = models.CharField(
        max_length=32,
        help_text="Name of the person the invoice should be sent to (required for non-complimentary invoices)",
        blank=True,
    )
    contact_email = models.EmailField(
        help_text="Email of the person the invoice should be sent to (required for non-complimentary invoices)",
        blank=True,
    )
    billing_address = models.TextField(
        help_text="The physical address of the client (required for non-complimentary invoices)",
        blank=True,
    )
    vat_number = models.CharField(
        max_length=32,
        help_text="The VAT number of the client (required for non-complimentary invoices)",
        blank=True,
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

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, tracked_properties=("total_amount_euros",), **kwargs
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
                check=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | Q(issued_on__isnull=False)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must set the 'Issued on' date.",
            ),
            models.CheckConstraint(
                name="internal_invoice_number_required_for_issued_payment_status",
                check=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | ~Q(internal_invoice_number="")
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must specify the internal invoice number.",
            ),
            models.CheckConstraint(
                name="internal_client_number_required_for_issued_payment_status",
                check=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | ~Q(internal_client_number="")
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must specify the internal client number.",
            ),
            models.CheckConstraint(
                name="paid_on_date_required_for_paid_payment_status",
                check=~Q(payment_status=PaymentStatusChoices.PAID)
                | Q(paid_on__isnull=False)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Paid',"
                " you must set the 'Paid on' date.",
            ),
            models.CheckConstraint(
                name="comments_required_for_complimentary_payment_type",
                check=~(
                    Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                    & Q(internal_comments="")
                ),
                violation_error_message="Please explain why the invoice is "
                "complimentary in the internal comments.",
            ),
            models.CheckConstraint(
                name="contact_name_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(contact_name=""),
                violation_error_message="Contact name is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="contact_email_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(contact_email=""),
                violation_error_message="Contact email is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="billing_address_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(billing_address=""),
                violation_error_message="Billing address is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="vat_number_required_for_non_complimentary_payment_type",
                check=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(vat_number=""),
                violation_error_message="VAT number is required for non-complimentary invoices.",
            ),
        ]

    @property
    def total_amount_euros(self):
        try:
            return (
                self.support_costs_euros
                + self.compute_costs_euros
                + self.storage_costs_euros
            )
        except TypeError:
            return None

    def clean(self):
        if not self._state.adding:
            if self.has_changed("total_amount_euros"):
                raise ValidationError(
                    "The total amount may not change. (You may only redistribute costs.)"
                )

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            self.assign_permissions()
        if (
            self.payment_type != PaymentTypeChoices.COMPLIMENTARY
            and (self.has_changed("payment_status") or adding)
            and self.payment_status == PaymentStatusChoices.ISSUED
        ):
            on_commit(
                send_challenge_invoice_issued_notification_emails.signature(
                    kwargs={"pk": self.pk}
                ).apply_async
            )

    def assign_permissions(self):
        assign_perm(
            f"view_{self._meta.model_name}",
            self.challenge.admins_group,
            self,
        )


class InvoiceUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)


class InvoiceGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_invoice"})

    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)
