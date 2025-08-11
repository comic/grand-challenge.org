import humanize
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def naturaldelta(value):
    return humanize.naturaldelta(value, months=False)

@register.filter
def precisedelta(value):
    return humanize.precisedelta(value, minimum_unit="milliseconds")

@register.filter
def timedifference(value):
    return (timezone.now() - value).days


@register.filter
def naturalsize(value):
    return humanize.naturalsize(value)
