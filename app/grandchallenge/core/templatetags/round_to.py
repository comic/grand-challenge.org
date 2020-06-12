from math import floor

from django import template

register = template.Library()


@register.filter
def round_to(x: int, to: float = 1.0) -> int:
    """Rounds a number down to the nearest multiple of `to`"""
    return int(floor(x / float(to))) * int(to)
