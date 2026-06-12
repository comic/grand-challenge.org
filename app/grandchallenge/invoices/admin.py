from django.contrib import admin
from django.db import models

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.core.templatetags.bleach import md2html
from grandchallenge.core.templatetags.costs import euro, millicents_to_euro
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


class IsExpiredFilter(admin.SimpleListFilter):
    title = "is expired"
    parameter_name = "is_expired"

    def lookups(self, request, model_admin):
        return [("1", "Yes"), ("0", "No")]

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(is_expired=True)
        elif self.value() == "0":
            return queryset.filter(is_expired=False)
        return queryset


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "challenge",
        "internal_invoice_number_display",
        "payment_type",
        "payment_status",
        "total_amount_euros",
        "percent_budget_consumed_display",
        "issued_on",
        "expires_on",
        "last_checked_on",
        "is_not_expired",
        "utilization_priority",
        "internal_comments",
    )
    list_filter = (
        OverdueListFilter,
        ToCheckFilter,
        IsExpiredFilter,
        "payment_status",
        "payment_type",
        "challenge__short_name",
    )
    fieldsets = [
        (
            None,
            {
                "fields": [
                    "created",
                    "challenge",
                    "payment_type",
                    "payment_status",
                    "utilization_priority",
                    "total_amount_euros",
                    "internal_comments",
                    "internal_invoice_number",
                    "internal_client_number",
                ]
            },
        ),
        (
            "Dates",
            {
                "fields": [
                    "issued_on",
                    "paid_on",
                    "last_checked_on",
                    "follow_up_on",
                    (
                        "expires_on",
                        "is_not_expired",
                    ),
                ]
            },
        ),
        (
            "Budget Costs",
            {
                "fields": [
                    "support_costs_euros",
                    "compute_costs_euros",
                    "storage_costs_euros",
                ]
            },
        ),
        (
            "Budget Usage",
            {
                "fields": [
                    "percent_budget_consumed_display",
                    "available_compute_cost",
                    "approved_compute_cost",
                    "consumed_compute_cost",
                    "write_off_compute_cost",
                ]
            },
        ),
        (
            "Billing details",
            {
                "fields": [
                    "external_reference",
                    "billing_address",
                    "contact_name",
                    "contact_email",
                    "vat_number",
                    "invoice_request_text",
                ]
            },
        ),
    ]
    autocomplete_fields = ("challenge",)
    readonly_fields = [
        "created",
        "invoice_request_text",
        "percent_budget_consumed_display",
        "available_compute_cost",
        "approved_compute_cost",
        "consumed_compute_cost",
        "write_off_compute_cost",
        "total_amount_euros",
        "is_not_expired",
        "utilization_priority",
    ]

    ordering = ["created"]

    @admin.display(description="Total")
    def total_amount_euros(self, obj):
        if obj.total_amount_euros:
            return euro(obj.total_amount_euros, decimal_places=0)
        else:
            return ""

    @admin.display(description="Number")  # Reduce column width
    def internal_invoice_number_display(self, obj):
        return obj.internal_invoice_number

    @admin.display(
        boolean=True, ordering="expires_on", description="Not expired"
    )
    def is_not_expired(self, obj):
        return not obj.is_expired

    def available_compute_cost(self, obj):
        return millicents_to_euro(obj.available_compute_cost_euro_millicents)

    def approved_compute_cost(self, obj):
        return millicents_to_euro(obj.approved_compute_cost_euro_millicents)

    def consumed_compute_cost(self, obj):
        return millicents_to_euro(obj.consumed_compute_cost_euro_millicents)

    def write_off_compute_cost(self, obj):
        return millicents_to_euro(obj.write_off_compute_cost_euro_millicents)

    @admin.display(ordering="utilization_priority")
    def utilization_priority(self, obj):
        return obj.utilization_priority

    @admin.display(description="Consumed budget")
    def percent_budget_consumed_display(self, obj):
        value = obj.percent_budget_consumed
        if value is None:
            return "-"
        return f"{value}%"

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
        return (
            super()
            .get_queryset(request)
            .with_overdue_status()
            .with_budget_authorization()
            .with_utilization_priority_per_challenge()
        )


admin.site.register(InvoiceUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(InvoiceGroupObjectPermission, GroupObjectPermissionAdmin)
