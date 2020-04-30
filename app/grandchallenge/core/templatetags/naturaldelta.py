import humanize
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def naturaldelta(value):
    return humanize.naturaldelta(value, months=False)
