from django import template
from django.template.defaultfilters import stringfilter
from django.template.loader import render_to_string
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def copy_button_only(value, title="Copy to clipboard"):
    return format_html(
        "<button "
        'type="button" '
        'class="btn btn-link text-dark p-0 mt-0 mb-1 mx-1 copy-btn shadow-none" '
        'data-copy="{value}" '
        'data-placement="left" '
        'title="{title}">'
        '<i class="far fa-copy"></i>'
        "</button>",
        value=value,
        title=title,
    )


@register.filter
@stringfilter
def copy_button(value, link=None):
    return render_to_string(
        "grandchallenge/partials/copy_button.html",
        context={
            "button": copy_button_only(value=value),
            "display_value": str(value).split("-", 1)[0],
            "link": link,
        },
    )
