{% spaceless %}
    {% load humanize %}
    {% load url %}
{% endspaceless %}
Your challenge {{ challenge.short_name }} has {{ num_is_overdue_soon }} onboarding task{{ num_is_overdue_soon|pluralize }} that {{ num_is_overdue_soon|pluralize:"is,are" }} due sometime in the next week.

To view and complete onboarding tasks go [here]({% url "challenge-onboarding-task-list" challenge_short_name=challenge.short_name %}).

Feel free to ask us for any assistance.
