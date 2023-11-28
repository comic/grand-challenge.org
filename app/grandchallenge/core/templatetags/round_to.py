from django import template

register = template.Library()


@register.filter
def round_to(x: int, to: float = 1.0) -> float:
    """Rounds a number down to the nearest multiple of `to`."""
    return to * (x // to)
