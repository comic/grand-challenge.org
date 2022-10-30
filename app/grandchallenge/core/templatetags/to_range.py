from django import template

register = template.Library()


@register.filter
def to_range(stop: int, step: int = 1):
    return range(0, stop, step)
