from django import template
from pydantic_core import MISSING

register = template.Library()


@register.filter
def is_missing(obj):
    return obj is MISSING
