from django import template
from django.utils.html import format_html

from grandchallenge.evaluation.templatetags.evaluation_extras import (
    split_first,
)

register = template.Library()


@register.filter
def copy_button(value, link=None):
    button = format_html(
        "<button "
        'class="btn btn-link text-dark p-0 m-0 mr-1 copy-btn shadow-none" '
        'data-copy="{}" '
        'data-placement="left" '
        'title="Copy to clipboard">'
        '<i class="far fa-copy"></i>'
        "</button>",
        value,
    )

    shortened = split_first(value, "-")

    if link:
        return button + format_html('<a href="{}">{}</a>', link, shortened)
    else:
        return button + format_html("{}", shortened)
