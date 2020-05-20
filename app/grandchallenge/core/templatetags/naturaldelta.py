import humanize
from django import template

register = template.Library()


@register.filter
def naturaldelta(value):
    return humanize.naturaldelta(value, months=False)
