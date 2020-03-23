from typing import Union

import bleach
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()


@register.filter
def clean(html: str):
    """Clean the html with bleach."""
    cleaned_html = bleach.clean(
        html,
        tags=settings.BLEACH_ALLOWED_TAGS,
        attributes=settings.BLEACH_ALLOWED_ATTRIBUTES,
        styles=settings.BLEACH_ALLOWED_STYLES,
        protocols=settings.BLEACH_ALLOWED_PROTOCOLS,
        strip=settings.BLEACH_STRIP,
    )

    return mark_safe(cleaned_html)


@register.filter
def md2html(markdown: Union[str, None]):
    """Convert markdown to clean html"""
    return clean(markdownify(markdown or ""))
