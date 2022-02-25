from django import template

register = template.Library()


@register.simple_tag
def get_help_text(obj, field):
    return obj._meta.get_field(field).help_text
