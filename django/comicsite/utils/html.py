""" HTML utilities for global use, which were not in django """

from re import match

from django.utils.html import escapejs


def escape_for_html_id(string):
    """ Make this string fit for use as an html ID or NAME token.
    
    Output for different strings should also be different, and output contains
    only alphanumeric and underscores
    """

    encoded = "".join([x for x in escapejs(string) if match("[\w ]", x)])
    no_spaces = encoded.replace(" ", "_")

    return no_spaces
