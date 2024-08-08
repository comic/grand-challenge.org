import json
from base64 import b64encode

from django import template

register = template.Library()


@register.filter
def b64encode_json(value):
    return b64encode(json.dumps(value).encode("utf-8")).decode("utf-8")
