from urllib.parse import urlparse

import bleach
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from markdown import markdown as render_markdown
from markdown.extensions.toc import TocExtension

from grandchallenge.core.utils.markdown import (
    EmbedYoutubeExtension,
    LinkBlankTargetExtension,
)

register = template.Library()


def allowed_iframe(tag, name, value):
    """Returns true if the iframe tag is allowed, false otherwise"""
    if tag != "iframe":
        return False
    if name in settings.BLEACH_ALLOWED_FRAME_ATTRIBUTES:
        return True
    if name == "src":
        p = urlparse(value)
        if not p.scheme or not p.netloc:
            return False
        source = f"{p.scheme}://{p.netloc}"
        if source in settings.BLEACH_ALLOWED_FRAME_SRC:
            return True
    return False


@register.filter
def clean(html: str, allow_iframes=False):
    """Clean the html with bleach."""

    allowed_tags = settings.BLEACH_ALLOWED_TAGS
    allowed_attributes = settings.BLEACH_ALLOWED_ATTRIBUTES

    if allow_iframes:
        allowed_tags = [*allowed_tags, "iframe"]
        allowed_attributes = {
            **allowed_attributes,
            "iframe": allowed_iframe,
        }

    cleaned_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        css_sanitizer=CSSSanitizer(
            allowed_css_properties=settings.BLEACH_ALLOWED_STYLES
        ),
        protocols=settings.BLEACH_ALLOWED_PROTOCOLS,
        strip=settings.BLEACH_STRIP,
    )

    return mark_safe(cleaned_html)


@register.filter
def md2email_html(markdown: str | None):
    """Converts markdown to clean html intended for emailing"""
    return md2html(
        markdown,
        link_blank_target=True,
        create_permalink_for_headers=False,
    )


@register.filter
def md2page_html(markdown: str | None):
    """Converts markdown to clean html intended for showing as a page"""
    return md2html(
        markdown,
        link_blank_target=True,
        create_permalink_for_headers=True,
        embed_youtube=True,
    )


@register.filter
def md2html(
    markdown: str | None,
    *,
    link_blank_target=False,
    create_permalink_for_headers=True,
    embed_youtube=False,
):
    """Convert markdown to clean html"""

    extensions = [*settings.MARKDOWNX_MARKDOWN_EXTENSIONS]

    if link_blank_target:
        extensions.append(LinkBlankTargetExtension())

    if create_permalink_for_headers:
        extensions.append(
            TocExtension(
                permalink=True,
                permalink_class="headerlink text-muted small pl-1",
            )
        )

    if embed_youtube:
        extensions.append(EmbedYoutubeExtension())

    html = render_markdown(
        text=markdown or "",
        extensions=extensions,
        extension_configs=settings.MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
    )

    return clean(html, allow_iframes=embed_youtube)
