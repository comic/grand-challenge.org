from pathlib import Path

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def suffix(value):
    return Path(value).suffix


@register.filter
@stringfilter
def stem(value):
    return Path(value).stem


@register.filter
@stringfilter
def name(value):
    return Path(value).name
