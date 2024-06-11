from django import template

register = template.Library()


@register.filter
def to_string(v):
    return str(v)


@register.filter
def line_count(value):
    if not isinstance(value, str):
        return 0
    return len(value.splitlines())
