We are pleased to let you know that we have received payment for a prepaid invoice for your challenge {{ invoice.challenge.short_name }}.

**Invoice details:**

- Amount: {{ invoice.total_amount_euros }} Euro
- Support cost: {{ invoice.support_costs_euros }} Euro
- Compute capacity reservation: {{ invoice.compute_costs_euros }} Euro
- Storage capacity reservation: {{ invoice.storage_costs_euros }} Euro

{% if invoice.compute_costs_euros > 0 %}
With this payment, a compute budget of {{ invoice.compute_costs_euros }} Euro has become available for your challenge.
You can now use this budget to process submissions.
{% endif %}

If you have any questions about your budget or invoices, please do not hesitate to reach out.
