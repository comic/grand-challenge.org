import json

from django import template
from django.utils.safestring import mark_safe
from jsonpath_rw import parse

register = template.Library()


@register.filter
def get_jsonpath(obj: dict, jsonpath):
    """
    Gets a value from a dictionary based on a jsonpath. It will only return
    one result, and if a key does not exist it will return an empty string as
    template tags should not raise errors.

    :param obj: The dictionary to query
    :param jsonpath: The path to the object (singular)
    :return: The most relevant object in the dictionary
    """
    try:
        expr = parse(jsonpath)
        return expr.find(obj)[0].value
    except (AttributeError, IndexError):
        return ''


@register.filter
def user_error(obj: str):
    """
    Filter an error message to just return the last, none-empty line. Used
    to return the last line of a traceback to a user.

    :param obj: A string with newlines
    :return: The last, none-empty line of obj
    """
    try:
        lines = list(filter(None, obj.split('\n')))
        return lines[-1]
    except IndexError:
        return obj


@register.filter
def json_dumps(obj: dict):
    """
    Dumps a json object
    :param obj: a dictionary
    :return:
    """
    try:
        return mark_safe(json.dumps(obj, indent=2))
    except TypeError:
        # Not json encodable
        return str(obj)
