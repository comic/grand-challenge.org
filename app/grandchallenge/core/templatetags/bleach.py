import bleach
from django import template
from django.utils.safestring import mark_safe

from config.settings import (
    BLEACH_ALLOWED_TAGS,
    BLEACH_ALLOWED_ATTRIBUTES,
    BLEACH_ALLOWED_STYLES,
    BLEACH_ALLOWED_PROTOCOLS,
)

register = template.Library()


@register.filter
def clean(html: str):
    """ Cleans the html with bleach """

    cleaned_html = bleach.clean(
        html,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRIBUTES,
        styles=BLEACH_ALLOWED_STYLES,
        protocols=BLEACH_ALLOWED_PROTOCOLS,
    )

    return mark_safe(cleaned_html)
