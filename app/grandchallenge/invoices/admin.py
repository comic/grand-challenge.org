import math

from django.contrib import admin, messages
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.template.defaultfilters import pluralize

from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.invoices.models import (
    Invoice,
    InvoiceGroupObjectPermission,
    InvoiceUserObjectPermission,
)


class DueStatusChoices(models.TextChoices):
    DUE = "DUE", "Due"
    OVERDUE = "OVERDUE", "Overdue"


class OverdueListFilter(admin.SimpleListFilter):
    title = "Due status"
    parameter_name = "due_status"

    def lookups(self, *_, **__):
        return DueStatusChoices.choices

    def queryset(self, request, queryset):
        if self.value() == DueStatusChoices.DUE:
            queryset = queryset.filter(is_due=True)
        elif self.value() == DueStatusChoices.OVERDUE:
            queryset = queryset.filter(is_overdue=True)
        return queryset


class ToCheckFilter(admin.SimpleListFilter):
    title = "to check"
    parameter_name = "to_check"

    def lookups(self, request, model_admin):
        return [("1", "Yes")]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.to_check()
        return queryset


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "challenge",
        "issued_on",
        "expires_on",
        "follow_up_on",
        "internal_invoice_number",
        "internal_client_number",
        "contact_email",
        "total_amount_euros",
        "payment_type",
        "payment_status",
        "paid_on",
        "last_checked_on",
        "internal_comments",
    )
    list_filter = (
        OverdueListFilter,
        ToCheckFilter,
        "payment_status",
        "payment_type",
        "challenge__short_name",
    )
    autocomplete_fields = ("challenge",)
    readonly_fields = ["invoice_request_text"]
    actions = ["calculate_postpaid_costs"]

    def has_delete_permission(self, request, obj=None):
        # invoices cannot be deleted
        return False

    def invoice_request_text(self, obj):
        required = {
            "Amount": f"{obj.total_amount_euros} Euro",
            "Billing address": obj.billing_address,
            "Contact person": obj.contact_name,
            "Contact email": obj.contact_email,
            "VAT number": obj.vat_number,
        }
        optional = {
            "Payment reference identifier": obj.external_reference,
        }

        warning_text = ""
        for key, value in required.items():
            if not value:
                warning_text += f"Warning: {key} is not provided.<br>"
        if warning_text:
            warning_text = f'<div class="errornote">{warning_text}</div>'

        invoice_request_details = '<div class="invoice-example-text">'

        invoice_request_details += f"See below for the billing information for the recently accepted {obj.challenge.short_name!r} challenge.<br><br>"

        for key, value in required.items():
            invoice_request_details += f"<strong>{key}</strong>:"
            invoice_request_details += f"<pre>{value}</pre>"
        for key, value in optional.items():
            if value:
                invoice_request_details += f"<strong>{key}</strong>:"
                invoice_request_details += f"<pre>{value}</pre>"

        invoice_request_details += "</div>"

        return md2html(warning_text + invoice_request_details)

    def get_queryset(self, request):
        return super().get_queryset(request).with_overdue_status()

    @admin.action(
        description="Calculate compute/storage costs for post-paid invoice"
    )
    def calculate_postpaid_costs(self, request, queryset):
        valid_invoices = list(
            queryset.filter(
                payment_type=Invoice.PaymentTypeChoices.POSTPAID,
                payment_status=Invoice.PaymentStatusChoices.INITIALIZED,
            ).select_related("challenge")
        )

        challenge_ids = [inv.challenge_id for inv in valid_invoices]
        if len(challenge_ids) != len(set(challenge_ids)):
            self.message_user(
                request,
                "You can only update one invoice per challenge at a time. Aborting action.",
                messages.ERROR,
            )
            return

        storage_costs_euros_per_gb = (
            ChallengeRequest().storage_costs_euros_per_gb
        )
        unused_budget_postpaid_invoices = []
        updated_invoices = []

        for invoice in valid_invoices:
            challenge = invoice.challenge
            total_compute = invoice.compute_cost_euro_millicents / 1000 / 100
            total_storage = storage_costs_euros_per_gb * (
                challenge.size_in_storage / 1024**3
                + challenge.size_in_registry / 1024**3
            )
            total_consumed = total_compute + total_storage

            paid_storage = (
                challenge.invoices.filter(
                    Q(payment_status=Invoice.PaymentStatusChoices.PAID)
                    | Q(payment_type=Invoice.PaymentTypeChoices.COMPLIMENTARY)
                )
                .exclude(pk=invoice.pk)
                .aggregate(
                    paid_storage=Coalesce(Sum("storage_costs_euros"), 0),
                )
            )["paid_storage"]

            unpaid_compute = total_compute
            unpaid_storage = total_storage - paid_storage
            unpaid_total = unpaid_compute + unpaid_storage

            if unpaid_total <= 0:
                unused_budget_postpaid_invoices.append(invoice)
                continue

            post_paid_total = math.ceil(unpaid_total / 250.0) * 250
            compute_ratio = total_compute / total_consumed
            storage_ratio = total_storage / total_consumed

            surplus = post_paid_total - unpaid_total

            invoice.compute_costs_euros = round(
                unpaid_compute + (surplus * compute_ratio)
            )
            invoice.storage_costs_euros = round(
                unpaid_storage + (surplus * storage_ratio)
            )

            # Distribute any rounding discrepancy from independently rounding
            # compute and storage onto compute to ensure the split sums to post_paid_total
            difference = post_paid_total - (
                invoice.compute_costs_euros + invoice.storage_costs_euros
            )
            invoice.compute_costs_euros += difference
            invoice.save(
                update_fields=["compute_costs_euros", "storage_costs_euros"]
            )
            updated_invoices.append(invoice)

        skipped_invoices_count = queryset.count() - len(valid_invoices)
        if skipped_invoices_count:
            self.message_user(
                request,
                f"{skipped_invoices_count} invoice{pluralize(skipped_invoices_count)} {pluralize(skipped_invoices_count, arg="was,were")} skipped because {pluralize(skipped_invoices_count, arg="it's,they're")} not POSTPAID and INITIALIZED.",
                messages.WARNING,
            )

        if unused_budget_postpaid_invoices:
            unused_budget_invoices_count = len(unused_budget_postpaid_invoices)
            self.message_user(
                request,
                f"{unused_budget_invoices_count} invoice{pluralize(unused_budget_invoices_count)} {pluralize(unused_budget_invoices_count, arg="was,were")} skipped as {pluralize(unused_budget_invoices_count, arg="its,their")} postpaid budget has not been used: {', '.join(str(inv.pk) for inv in unused_budget_postpaid_invoices)}",
                messages.WARNING,
            )

        if updated_invoices:
            updated_invoices_count = len(updated_invoices)
            self.message_user(
                request,
                f"{updated_invoices_count} postpaid invoice{pluralize(updated_invoices_count)} {pluralize(updated_invoices_count, arg="was,were")} updated: {', '.join(str(inv.pk) for inv in updated_invoices)}",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request, "No invoices were updated.", messages.WARNING
            )


admin.site.register(InvoiceUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(InvoiceGroupObjectPermission, GroupObjectPermissionAdmin)
