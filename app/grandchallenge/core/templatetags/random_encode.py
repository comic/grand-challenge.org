import random

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def random_encode(value):
    """Randomly replace letters with their html encoded equivalents."""
    return "".join(random.choice([f"&#{ord(c)};", c]) for c in value)
