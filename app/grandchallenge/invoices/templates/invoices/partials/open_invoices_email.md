{% load url %}
The following invoices need to be checked:
{% if post_paid_invoices_to_follow_up %}
Unprocessed post-paid invoices with a follow-up date in the past:
{% for invoice in post_paid_invoices_to_follow_up %} {{ invoice }}: {% url 'admin:invoices_invoice_change' invoice.pk %}
{% endfor %}{% endif %}
{% if initialized_prepaid_invoices %}
Initialized prepaid:
{% for invoice in initialized_prepaid_invoices %} {{ invoice }}: {% url 'admin:invoices_invoice_change' invoice.pk %}
{% endfor %}{% endif %}
{% if requested_invoices %}
Requested invoices:
{% for invoice in requested_invoices %} {{ invoice }}: {% url 'admin:invoices_invoice_change' invoice.pk %}
{% endfor %}{% endif %}
{% if issued_invoices %}
Issued invoices:
{% for invoice in issued_invoices %} {{ invoice }}: {% url 'admin:invoices_invoice_change' invoice.pk %}
{% endfor %}{% endif %}
