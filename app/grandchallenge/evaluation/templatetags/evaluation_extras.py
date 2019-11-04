import json

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from grandchallenge.teams.models import Team

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
        keys = jsonpath.split(".")
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
def user_error(obj: [str, bytes]):
    """
    Filter an error message to just return the last, none-empty line. Used
    to return the last line of a traceback to a user.

    :param obj: A string with newlines
    :return: The last, none-empty line of obj
    """
    try:
        # Sometimes bytes gets passed to this function, so try to decode it
        obj = obj.decode()
    except AttributeError:
        pass

    try:
        lines = list(filter(None, obj.split("\n")))
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


@register.filter
def get_team_html(obj):
    try:
        team = Team.objects.get(
            challenge=obj.job.submission.challenge,
            teammember__user=obj.job.submission.creator,
        )
        return format_html(
            '<a href="{}">{}</a>', team.get_absolute_url(), team.name
        )

    except Exception:
        return ""
