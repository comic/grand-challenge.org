Your challenge request has been sent to the reviewers. You will receive an email informing you of our decision within the next 4 weeks.
The reviewers might contact you for additional information during that time. You can track the status of your request [here]({{ link }}).

We have calculated the following budget estimate. This estimate is based on the information you provided in the form and reflects a rough estimation of the costs we expect to incur:

{% for key, value in budget.items %}
- {{ key }}: {{ value }} €
{% endfor %}
