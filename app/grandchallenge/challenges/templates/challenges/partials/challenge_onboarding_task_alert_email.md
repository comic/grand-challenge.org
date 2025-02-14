{% load humanize url %}
Your challenge {{ challenge.short_name }} has {{ num_is_overdue }} onboarding task{{ num_is_overdue|pluralize }} that {{ num_is_overdue|pluralize:"is,are" }} overdue.

Please complete them as soon as possible: the due date was {{ min_deadline|naturaltime }}.

To view and complete onboarding tasks go [here]({% url "challenge-onboarding-task-list" challenge_short_name=challenge.short_name %}).

Feel free to ask us for any assistance.
