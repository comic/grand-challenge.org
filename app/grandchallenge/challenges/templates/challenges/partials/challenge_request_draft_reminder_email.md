{% load url %}
This is an automated reminder that your challenge request for hosting {{ challenge_request.short_name }}, titled "{{ challenge_request.title }}", has not yet been submitted.

To finish and submit the request, please go [here]({% url "challenges:requests-detail" pk=challenge_request.pk %}).

If you need any assistance or would like us to delete the request, please contact us.
