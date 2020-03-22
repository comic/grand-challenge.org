from django import template

register = template.Library()


@register.filter
def meta_attr(obj, key):
    """Returns an attribute of an objects _meta class"""
    return getattr(obj._meta, key, "")
