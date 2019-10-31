from pathlib import Path

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def suffix(value):
    return Path(value).suffix
