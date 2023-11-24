from django import template
from django.template.loader import render_to_string

from grandchallenge.core.utils.tag_substitutions import TagSubstitution

register = template.Library()

process_youtube_tags = TagSubstitution(
    tag_name="youtube",
    replacement=lambda _id: render_to_string(
        "partials/youtube_embed.html",
        context={
            "youtube_id": _id,
        },
    ),
)


@register.filter
def process_tags(html: str):
    for processor in [
        process_youtube_tags,
    ]:
        html = processor(html)
    return html
