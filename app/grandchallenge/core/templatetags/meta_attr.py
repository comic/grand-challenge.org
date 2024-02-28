from django import template

register = template.Library()


@register.filter
def meta_attr(obj, key):
    """Returns an attribute of an objects _meta class"""
    return getattr(obj._meta, key, "")


@register.filter
def verbose_name(obj):
    return obj._meta.verbose_name


@register.filter
def verbose_name_plural(obj):
    return obj._meta.verbose_name_plural


@register.filter
def model_name(obj):
    return obj._meta.model_name
