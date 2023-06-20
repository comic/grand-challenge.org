from django import template

register = template.Library()


@register.filter
def to_string(v):
    return str(v)
