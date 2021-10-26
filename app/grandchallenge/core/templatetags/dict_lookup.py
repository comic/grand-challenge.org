from django import template

register = template.Library()


@register.simple_tag
def get_dict_values(dictionary, key):
    try:
        return dictionary.get(key)
    except AttributeError:
        return None
