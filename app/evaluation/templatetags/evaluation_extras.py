from django import template

register = template.Library()

@register.filter
def get(obj: dict, key):
    return obj.get(key, '')
