from django import template

register = template.Library()


@register.simple_tag
def get_help_text(obj, field):
    return obj.get_help_text(field)
