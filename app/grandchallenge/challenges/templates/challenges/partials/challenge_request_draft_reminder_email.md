{% load url %}
Your challenge request for hosting the challenge {{ challenge_request.short_name }}, titled ('{{ challenge_request.title }}') is yet unfinished.

To finish and submit the request go [here]({% url "challenges:requests-detail" pk=challenge_request.pk %}).

Feel free to ask us for any assistance.
