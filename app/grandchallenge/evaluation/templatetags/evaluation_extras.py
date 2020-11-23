import json

from django import template

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
        keys = str(jsonpath).split(".")
        val = obj

        for key in keys:
            val = val[key]

        return val

    except KeyError:
        return ""


@register.filter
def get_key(obj: dict, key):
    try:
        return obj[key]
    except KeyError:
        return ""


@register.filter
def json_dumps(obj: dict):
    """
    Dumps a json object
    :param obj: a dictionary
    :return:
    """
    try:
        return json.dumps(obj, indent=2)

    except TypeError:
        # Not json encodable
        return str(obj)
