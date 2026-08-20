from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import SafeString
from justhtml import JustHTML, SanitizationPolicy, UrlPolicy, UrlRule
from justhtml.transforms import EditAttrs
from markdown import markdown as render_markdown
from markdown.extensions.toc import TocExtension

from grandchallenge.core.utils.markdown import LinkBlankTargetExtension
from grandchallenge.core.utils.tag_substitutions import TagSubstitution

register = template.Library()


@register.filter
def clean(html: str, *, no_tags=False):
    """Sanitizes untrusted html"""
    if no_tags:
        allowed_tags = frozenset()
        allowed_attributes = {}
        allowed_css_properties = frozenset()
        allow_rules = {}
    else:
        allowed_tags = frozenset(
            {
                "a",
                "abbr",
                "acronym",
                "b",
                "blockquote",
                "br",
                "code",
                "col",
                "del",
                "div",
                "em",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "hr",
                "i",
                "img",
                "li",
                "ol",
                "p",
                "pre",
                "span",
                "strike",
                "strong",
                "sub",
                "table",
                "tbody",
                "thead",
                "td",
                "th",
                "tr",
                "u",
                "ul",
                "video",
            }
        )

        allowed_attributes = {
            "*": ["class", "data-toggle", "id", "style", "role"],
            "a": ["href", "title", "target", "rel", "data-target"],
            "abbr": ["title"],
            "acronym": ["title"],
            "img": ["height", "src", "width"],
            # For bootstrap tables: https://getbootstrap.com/docs/4.3/content/tables/
            "th": ["scope", "colspan"],
            "td": ["colspan"],
            "video": ["src", "loop", "controls", "poster"],
        }

        allowed_css_properties = frozenset({"height", "width"})

        allow_rules = {
            key: UrlRule(
                allowed_schemes=frozenset({"http", "https", "mailto"})
            )
            for key in {
                ("a", "href"),
                ("img", "src"),
                ("video", "src"),
                ("video", "poster"),
            }
        }

    policy = SanitizationPolicy(
        allowed_tags=allowed_tags,
        allowed_attributes=allowed_attributes,
        allowed_css_properties=allowed_css_properties,
        url_policy=UrlPolicy(allow_rules=allow_rules),
    )

    cleaned_html = JustHTML(
        html=html,
        fragment=True,
        policy=policy,
        transforms=[
            EditAttrs("a[target=_blank]", _add_noopener_to_blank_target),
        ],
    ).to_html(pretty=False)

    from django.utils.safestring import (  # noqa I251: we're sure that the strings are safe here as they have been cleaned
        mark_safe,
    )

    return mark_safe(cleaned_html)


def _add_noopener_to_blank_target(node):
    attrs = dict(node.attrs) if node.attrs else {}
    rel = attrs.get("rel", "")
    tokens = rel.split() if rel else []

    if "noopener" not in tokens:
        tokens.append("noopener")
        attrs["rel"] = " ".join(tokens)
        return attrs
    else:
        return None


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
