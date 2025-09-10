import bleach
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe
from markdown import markdown as render_markdown
from markdown.extensions.toc import TocExtension

from grandchallenge.core.utils.markdown import LinkBlankTargetExtension
from grandchallenge.core.utils.tag_substitutions import TagSubstitution

register = template.Library()


@register.filter
def clean(html: str, *, no_tags=False):
    """Clean the html with bleach."""
    if no_tags:
        tags = []
    else:
        tags = settings.BLEACH_ALLOWED_TAGS

    cleaned_html = bleach.clean(
        html,
        tags=tags,
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
        process_youtube_tags=False,
    )


YOUTUBE_TAG_SUBSTITUTION = TagSubstitution(
    tag_name="youtube",
    replacement=lambda youtube_id: render_to_string(
        "grandchallenge/partials/youtube_embed.html",
        context={
            "youtube_id": youtube_id,
        },
    ),
)


@register.filter
def md2html(
    markdown: str | None,
    *,
    link_blank_target=False,
    create_permalink_for_headers=True,
    process_youtube_tags=True,
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
        tab_length=2,
    )

    cleaned_html = clean(html)

    post_processors = [*settings.MARKDOWN_POST_PROCESSORS]

    if process_youtube_tags:
        post_processors.append(YOUTUBE_TAG_SUBSTITUTION)

    for processor in post_processors:
        cleaned_html = processor(cleaned_html)

    if not isinstance(cleaned_html, SafeString):
        raise RuntimeError("Markdown rendering failed to produce a SafeString")

    return cleaned_html
