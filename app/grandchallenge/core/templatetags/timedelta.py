from django import template

register = template.Library()


@register.filter
def total_hours(timedelta):
    return timedelta.total_seconds() / 3600
