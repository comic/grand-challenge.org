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

    except (KeyError, TypeError):
        return ""


@register.filter
def get_key(obj: dict, key):
    try:
        return obj[key]
    except (KeyError, TypeError):
        return ""


@register.filter
def split_first(object, character):
    return str(object).split(character, 1)[0]
