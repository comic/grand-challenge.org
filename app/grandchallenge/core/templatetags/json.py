import json

from django import template

register = template.Library()


@register.filter
def json_dumps(obj: dict, indent: int = 2):
    try:
        return json.dumps(obj, indent=indent)

    except TypeError:
        # Not json encodable
        return str(obj)
