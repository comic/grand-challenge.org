from django import template

from grandchallenge.components.backends.utils import (
    user_error as component_user_error,
)

register = template.Library()


@register.filter
def user_error(arg):
    return component_user_error(arg)
