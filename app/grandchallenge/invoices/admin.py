from django.contrib import admin

from grandchallenge.invoices.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "challenge",
        "issued_on",
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
    list_filter = ("payment_status",)
    autocomplete_fields = ("challenge",)

    def total_amount_euros(self, obj):
        return (
            obj.support_costs_euros
            + obj.compute_costs_euros
            + obj.storage_costs_euros
        )
