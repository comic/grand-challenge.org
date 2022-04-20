import humanize
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def naturaldelta(value):
    return humanize.naturaldelta(value, months=False)


@register.filter
def timedifference(value):
    return (timezone.now() - value).days
