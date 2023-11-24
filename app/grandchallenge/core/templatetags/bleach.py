import bleach
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from markdown import markdown as render_markdown
from markdown.extensions.toc import TocExtension

from grandchallenge.core.templatetags.process_tags import process_tags
from grandchallenge.core.utils.markdown import LinkBlankTargetExtension

register = template.Library()


@register.filter
def clean(html: str):
    """Clean the html with bleach."""
    cleaned_html = bleach.clean(
        html,
        tags=settings.BLEACH_ALLOWED_TAGS,
        attributes=settings.BLEACH_ALLOWED_ATTRIBUTES,
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


def md2html_with_tag_processing(*args, **kwargs):
    """Converts markdown to clean html and passes it through custom tag processing"""
    return process_tags(md2html(*args, **kwargs))


@register.filter
def md2html(
    markdown: str | None,
    *,
    link_blank_target=False,
    create_permalink_for_headers=True,
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

    html = render_markdown(
        text=markdown or "",
        extensions=extensions,
        extension_configs=settings.MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
    )

    return clean(html)
