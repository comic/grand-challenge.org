{% load humanize url %}
Your challenge request for hosting the challenge {{ challenge_request.short_name }}, titled ('{{ challenge_request.title }}') has not yet been submited for review.

To complete and submit the request go [here]({% url "challenges:requests-detail" pk=challenge_request.pk %}).

Feel free to ask us for any assistance.
