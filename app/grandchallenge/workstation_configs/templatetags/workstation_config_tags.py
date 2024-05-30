from django import template

register = template.Library()


@register.simple_tag
def get_help_text(obj, field):
    return obj._meta.get_field(field).help_text


@register.simple_tag
def get_verbose_name(obj, field):
    return obj._meta.get_field(field).verbose_name.capitalize()


@register.filter(name="field_type")
def field_type(obj, field_name):
    field = obj._meta.get_field(field_name)
    return type(field).__name__


@register.filter(name="field_value")
def field_value(obj, name):
    result = getattr(obj, name, None)
    if isinstance(result, object) and hasattr(result, "all"):
        result = result.all()
    return result
