from django import template

register = template.Library()


@register.simple_tag
def get_dict_values(dictionary, key):
    return dictionary.get(key)
