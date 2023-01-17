from django import template

register = template.Library()


@register.filter
def divide_by(num, divisor):
    return num / divisor
