from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def remove_whitespace(value):
    return "".join(value.split())


@register.filter
def oxford_comma(items):
    if len(items) > 2:
        return ", and ".join([", ".join(items[:-1]), items[-1]])
    elif len(items) == 2:
        return " and ".join(items)
    elif len(items) == 1:
        return items[0]
    else:
        return ""
