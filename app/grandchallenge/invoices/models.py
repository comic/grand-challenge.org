import math
import uuid
from datetime import timedelta
from functools import cached_property

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    Count,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
    Window,
)
from django.db.models.functions import Cast, Now, RowNumber
from django.utils.html import format_html
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.challenges.emails import (
    send_email_percent_budget_consumed_alert,
)
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
    def delete(self):
        raise ValidationError("Invoices cannot be deleted.")

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

    def with_budget_authorization(self):

        has_paid_prepaid_invoice = Exists(
            Invoice.objects.filter(
                challenge_id=OuterRef("challenge_id"),
                compute_costs_euros__gt=0,
                payment_type=PaymentTypeChoices.PREPAID,
                payment_status=PaymentStatusChoices.PAID,
            )
        )

        return self.with_is_expired().annotate(
            is_budget_authorized=ExpressionWrapper(
                ~Q(payment_status=PaymentStatusChoices.CANCELLED)
                & (
                    Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                    | Q(
                        payment_type=PaymentTypeChoices.PREPAID,
                        payment_status=PaymentStatusChoices.PAID,
                    )
                    | (
                        Q(payment_type=PaymentTypeChoices.POSTPAID)
                        & (
                            Q(payment_status=PaymentStatusChoices.PAID)
                            | has_paid_prepaid_invoice
                        )
                    )
                ),
                output_field=models.BooleanField(),
            )
        )

    def with_is_expired(self):
        return self.annotate(is_expired=Q(expires_on__lt=Now()))

    def to_check(self):
        return self.filter(
            Q(payment_status=Invoice.PaymentStatusChoices.REQUESTED)
            | Q(payment_status=Invoice.PaymentStatusChoices.ISSUED)
            | Q(
                payment_type=Invoice.PaymentTypeChoices.PREPAID,
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
            )
            | Q(
                payment_type=Invoice.PaymentTypeChoices.POSTPAID,
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
                follow_up_on__lte=now().date(),
            )
        )

    def with_utilization_priority_per_challenge(self):
        return self.annotate(
            is_paid=Q(payment_status=Invoice.PaymentStatusChoices.PAID)
        ).annotate(
            utilization_priority=Window(
                expression=RowNumber(),
                partition_by=[F("challenge_id")],
                order_by=["-is_paid", "expires_on", "created"],
            )
        )


def default_invoice_expiry():
    return now().date() + relativedelta(
        years=settings.CHALLENGE_INVOICES_DEFAULT_EXPIRE_AFTER_YEARS
    )


class Invoice(models.Model, FieldChangeMixin):
    objects = InvoiceQuerySet.as_manager()

    external_pk = models.UUIDField(
        # Use external_pk as lookups from the outside,
        # This is to prevent enumeration attacks via the default incremental
        # integer PK.
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    expires_on = models.DateField(
        help_text="The date when the invoice expires",
        default=default_invoice_expiry,
    )
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
        help_text="The date when the status of issued invoices was last checked",
        blank=True,
        null=True,
    )
    follow_up_on = models.DateField(
        help_text="The date when a post-paid invoice will be issued if necessary (required for post-paid invoices).",
        null=True,
        blank=True,
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
    compute_cost_euro_millicents = models.PositiveBigIntegerField(
        help_text="The utilized compute costs in Euro millicents (cached from utilizations)",
        default=0,
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
        choices=PaymentTypeChoices,
        default=PaymentTypeChoices.PREPAID,
    )
    PaymentStatusChoices = PaymentStatusChoices
    payment_status = models.CharField(
        max_length=11,
        choices=PaymentStatusChoices,
        default=PaymentStatusChoices.INITIALIZED,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(payment_type__in=PaymentTypeChoices.values),
                name="payment_type_in_choices",
            ),
            models.CheckConstraint(
                condition=Q(payment_status__in=PaymentStatusChoices.values),
                name="payment_status_in_choices",
            ),
            models.CheckConstraint(
                name="issued_on_date_required_for_issued_payment_status",
                condition=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | Q(issued_on__isnull=False)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must set the 'Issued on' date.",
            ),
            models.CheckConstraint(
                name="internal_invoice_number_required_for_issued_payment_status",
                condition=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | ~Q(internal_invoice_number="")
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must specify the internal invoice number.",
            ),
            models.CheckConstraint(
                name="internal_client_number_required_for_issued_payment_status",
                condition=~Q(payment_status=PaymentStatusChoices.ISSUED)
                | ~Q(internal_client_number="")
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Issued',"
                " you must specify the internal client number.",
            ),
            models.CheckConstraint(
                name="paid_on_date_required_for_paid_payment_status",
                condition=~Q(payment_status=PaymentStatusChoices.PAID)
                | Q(paid_on__isnull=False)
                | Q(payment_type=PaymentTypeChoices.COMPLIMENTARY),
                violation_error_message="When setting the payment status to 'Paid',"
                " you must set the 'Paid on' date.",
            ),
            models.CheckConstraint(
                name="comments_required_for_complimentary_payment_type",
                condition=~(
                    Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                    & Q(internal_comments="")
                ),
                violation_error_message="Please explain why the invoice is "
                "complimentary in the internal comments.",
            ),
            models.CheckConstraint(
                name="paid_or_cancelled_status_required_for_complimentary_payment_type",
                condition=~Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | Q(payment_status=PaymentStatusChoices.PAID)
                | Q(payment_status=PaymentStatusChoices.CANCELLED),
                violation_error_message="Complimentary invoices must have a 'Paid' or 'Cancelled' status.",
            ),
            models.CheckConstraint(
                name="contact_name_required_for_non_complimentary_payment_type",
                condition=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(contact_name=""),
                violation_error_message="Contact name is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="contact_email_required_for_non_complimentary_payment_type",
                condition=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(contact_email=""),
                violation_error_message="Contact email is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="billing_address_required_for_non_complimentary_payment_type",
                condition=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(billing_address=""),
                violation_error_message="Billing address is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="vat_number_required_for_non_complimentary_payment_type",
                condition=Q(payment_type=PaymentTypeChoices.COMPLIMENTARY)
                | ~Q(vat_number=""),
                violation_error_message="VAT number is required for non-complimentary invoices.",
            ),
            models.CheckConstraint(
                name="follow_up_on_before_expires_on",
                condition=Q(follow_up_on__isnull=True)
                | Q(follow_up_on__lt=F("expires_on")),
                violation_error_message="Follow-up date must be before the expiry date.",
            ),
            models.CheckConstraint(
                name="follow_up_on_not_more_than_a_year_in_future",
                condition=Q(follow_up_on__isnull=True)
                | Q(follow_up_on__lte=Now() + timedelta(days=365)),
                violation_error_message="Follow-up date cannot be more than a year into the future.",
            ),
            models.CheckConstraint(
                name="follow_up_on_required_for_initialized_post_paid",
                condition=~Q(payment_type=PaymentTypeChoices.POSTPAID)
                | ~Q(payment_status=PaymentStatusChoices.INITIALIZED)
                | Q(follow_up_on__isnull=False),
                violation_error_message="Follow-up date is required for initialized post-paid invoices.",
            ),
        ]

        indexes = [
            models.Index(fields=["external_pk"]),
        ]

    def delete(self, *args, **kwargs):
        raise ValidationError("Invoices cannot be deleted.")

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

    @property
    def _current_state(self):
        state = super()._current_state
        state["total_amount_euros"] = self.total_amount_euros
        return state

    def get_status_badge(self):
        return format_html(
            '<span class="badge badge-{badge_class}">{text}</span>',
            badge_class=self._status_badge_class,
            text=self._status_badge_text,
        )

    @property
    def _status_badge_text(self):
        payment_type = self.payment_type
        payment_status = self.payment_status

        if self.is_expired:
            return "Expired"
        elif payment_type == PaymentTypeChoices.PREPAID and payment_status in (
            PaymentStatusChoices.INITIALIZED,
            PaymentStatusChoices.REQUESTED,
        ):
            return "Initialized"
        elif (
            payment_type == PaymentTypeChoices.POSTPAID
            and payment_status
            in (
                PaymentStatusChoices.INITIALIZED,
                PaymentStatusChoices.REQUESTED,
            )
        ):
            return "Reserved"
        else:
            return self.get_payment_status_display()

    @property
    def _status_badge_class(self):
        payment_type = self.payment_type
        payment_status = self.payment_status

        if payment_status == PaymentStatusChoices.CANCELLED or self.is_expired:
            return "danger"
        elif payment_type == PaymentTypeChoices.COMPLIMENTARY:
            return "success"
        elif payment_status == PaymentStatusChoices.PAID:
            return "success"
        elif payment_type == PaymentTypeChoices.POSTPAID:
            return "success"
        else:
            return "info"

    @cached_property
    def available_compute_cost_euro_millicents(self):
        if self.is_expired:
            return 0
        else:
            return (
                self.approved_compute_cost_euro_millicents
                - self.consumed_compute_cost_euro_millicents
            )

    @cached_property
    def approved_compute_cost_euro_millicents(self):
        return (
            self.compute_costs_euros * 1000 * 100
            if self.is_budget_authorized
            else 0
        )

    @cached_property
    def approved_storage_cost_euro_millicents(self):
        return (
            self.storage_costs_euros * 1000 * 100
            if self.is_budget_authorized
            else 0
        )

    @cached_property
    def consumed_compute_cost_euro_millicents(self):
        return min(
            self.compute_cost_euro_millicents,
            self.approved_compute_cost_euro_millicents,  # Cap
        )

    @cached_property
    def write_off_compute_cost_euro_millicents(self):
        balance = (
            self.approved_compute_cost_euro_millicents
            - self.compute_cost_euro_millicents
        )
        return abs(min(balance, 0))

    @cached_property
    def percent_compute_budget_consumed(self):
        if self.approved_compute_cost_euro_millicents > 0:
            return int(
                100
                * self.consumed_compute_cost_euro_millicents
                / self.approved_compute_cost_euro_millicents
            )
        else:
            return None

    @cached_property
    def total_unpaid_costs_euro_millicents(self):
        if (
            not self.payment_type == PaymentTypeChoices.POSTPAID
            or not self.payment_status == PaymentStatusChoices.INITIALIZED
        ):
            return NotImplementedError
        else:
            return (
                self.challenge.unpaid_storage_costs_euro_millicents
                + self.consumed_compute_cost_euro_millicents
            )

    @cached_property
    def suggested_total_postpaid_amount_euro_millicents(self):
        if (
            not self.payment_type == PaymentTypeChoices.POSTPAID
            or not self.payment_status == PaymentStatusChoices.INITIALIZED
        ):
            return NotImplementedError
        elif self.total_unpaid_costs_euro_millicents > 0:
            return (
                math.ceil(
                    self.total_unpaid_costs_euro_millicents
                    / settings.CHALLENGE_POSTPAID_INVOICE_ROUNDING_INCREMENT
                )
                * settings.CHALLENGE_POSTPAID_INVOICE_ROUNDING_INCREMENT
            )
        else:
            return 0

    @cached_property
    def surplus_euro_millicents(self):
        if (
            not self.payment_type == PaymentTypeChoices.POSTPAID
            or not self.payment_status == PaymentStatusChoices.INITIALIZED
        ):
            return NotImplementedError
        elif self.total_unpaid_costs_euro_millicents > 0:
            return (
                settings.CHALLENGE_POSTPAID_INVOICE_ROUNDING_INCREMENT
                - self.total_unpaid_costs_euro_millicents
            )
        else:
            return 0

    @cached_property
    def suggested_compute_cost_euro_millicents(self):
        if (
            not self.payment_type == PaymentTypeChoices.POSTPAID
            or not self.payment_status == PaymentStatusChoices.INITIALIZED
        ):
            return NotImplementedError
        else:
            return round(
                (
                    self.consumed_compute_cost_euro_millicents
                    + self.challenge.compute_cost_share
                    * self.surplus_euro_millicents
                ),
                0,
            )

    @cached_property
    def suggested_storage_cost_euro_millicents(self):
        if (
            not self.payment_type == PaymentTypeChoices.POSTPAID
            or not self.payment_status == PaymentStatusChoices.INITIALIZED
        ):
            return NotImplementedError
        else:
            return (
                self.suggested_total_postpaid_amount_euro_millicents
                - self.suggested_compute_cost_euro_millicents
            )

    def clean(self):
        if (
            not self._state.adding
            and self.payment_type != PaymentTypeChoices.COMPLIMENTARY
            and self.initial_value("payment_status")
            != PaymentStatusChoices.INITIALIZED
        ):
            # Assert total amount unchanged
            if (
                self._current_state["total_amount_euros"]
                != self._initial_state["total_amount_euros"]
            ):
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
            send_challenge_invoice_issued_notification_emails.execute_on_commit(
                pk=self.pk
            )

        if self.has_changed("compute_cost_euro_millicents"):
            self.send_alert_if_budget_consumed_warning_threshold_exceeded()

    def assign_permissions(self):
        assign_perm(
            f"view_{self._meta.model_name}",
            self.challenge.admins_group,
            self,
        )

    def send_alert_if_budget_consumed_warning_threshold_exceeded(self):
        for percent_threshold in sorted(
            self.challenge.percent_budget_consumed_warning_thresholds,
            reverse=True,
        ):
            previous_cost = self.initial_value("compute_cost_euro_millicents")
            threshold = (
                self.approved_compute_cost_euro_millicents
                * percent_threshold
                / 100
            )
            current_cost = self.compute_cost_euro_millicents
            if previous_cost <= threshold < current_cost:
                send_email_percent_budget_consumed_alert(
                    invoice=self,
                    percent_threshold=percent_threshold,
                )
                break


class InvoiceUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)


class InvoiceGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_invoice"})

    content_object = models.ForeignKey(Invoice, on_delete=models.CASCADE)
