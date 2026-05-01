from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import format_html

register = template.Library()


@register.filter
@stringfilter
def copy_pk_button(value, link=None):
    button = format_html(
        "<button "
        'type="button"'
        'class="btn btn-link text-dark p-0 m-0 mr-1 copy-btn shadow-none" '
        'data-copy="{value}" '
        'data-placement="left" '
        'title="Copy to clipboard">'
        '<i class="far fa-copy"></i>'
        "</button>",
        value=value,
    )

    shortened = str(value).split("-", 1)[0]

    if link:
        return button + format_html(
            '<a href="{link}">{display_value}</a>',
            link=link,
            display_value=shortened,
        )
    else:
        return button + format_html("{display_value}", display_value=shortened)
