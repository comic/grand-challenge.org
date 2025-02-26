from django.contrib import admin

from grandchallenge.core.templatetags.bleach import md2html
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
    readonly_fields = ["invoice_request_text"]

    def total_amount_euros(self, obj):
        return (
            obj.support_costs_euros
            + obj.compute_costs_euros
            + obj.storage_costs_euros
        )

    def invoice_request_text(self, obj):
        required = {
            "Amount": f"{self.total_amount_euros(obj)} Euro",
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
                warning_text += f"Warning: {key} is not provided.\n"
        warning_text += "\n\n" if warning_text else ""

        invoice_request_details = f"See below for the billing information for the recently accepted {obj.challenge.short_name!r} challenge.\n\n"

        invoice_request_details += "<table>\n"
        for key, value in required.items():
            value = value.replace("\n", "<br>")
            invoice_request_details += (
                f"<tr>\n"
                f"  <td><b>{key}:</b></td>\n"
                f"  <td>{value}</td>\n"
                f"</tr>\n"
            )
        for key, value in optional.items():
            if value:
                value = value.replace("\n", "<br>")
                invoice_request_details += (
                    f"<tr>\n"
                    f"  <td><b>{key}:</b></td>\n"
                    f"  <td>{value}</td>\n"
                    f"</tr>\n"
                )
        invoice_request_details += "</table>\n"

        return md2html(warning_text + invoice_request_details)
