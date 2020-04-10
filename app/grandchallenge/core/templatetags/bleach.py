from typing import Union

import bleach
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from markdown import markdown as render_markdown

from grandchallenge.core.utils.markdown import LinkBlankTargetExtension

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
def md2html(markdown: Union[str, None], link_blank_target=False):
    """Convert markdown to clean html"""

    extensions = settings.MARKDOWNX_MARKDOWN_EXTENSIONS

    if link_blank_target:
        extensions.append(LinkBlankTargetExtension())

    html = render_markdown(
        text=markdown or "",
        extensions=extensions,
        extension_configs=settings.MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
    )

    return clean(html)
