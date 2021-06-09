from hashlib import md5
from typing import Union
from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.utils.html import format_html
from machina.apps.forum.models import Forum

register = template.Library()


@register.filter
def forum_link(forum: Union[Forum, None]) -> str:

    if forum.challenge.logo:
        forum_name = forum.name
        forum_url = forum.get_absolute_url()
        challenge_logo = format_html(
            (
                '<img class="rounded-circle align-middle" loading="lazy" '
                'src="{0}" alt="Challenge logo" '
                'style="height: 1.33em;"/>'
            ),
            forum.challenge.logo.url,
        )
    else:
        forum_name = forum.name
        forum_url = forum.get_absolute_url()
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + md5(forum.name.lower().encode("utf-8")).hexdigest()
            + "?"
        )
        gravatar_url += urlencode(
            {"d": "identicon", "s": str(settings.PROFILES_MUGSHOT_SIZE)}
        )
        challenge_logo = format_html(
            (
                '<img class="rounded-circle align-middle" loading="lazy" '
                'src="{0}" alt="Challenge logo" '
                'style="height: 1.33em;"/>'
            ),
            gravatar_url,
        )

    return format_html(
        '<span class="text-nowrap"><a href="{0}">{1}</a>&nbsp;&nbsp;<a href="{0}">{2}</a></span>',
        forum_url,
        challenge_logo,
        forum_name,
    )


@register.simple_tag
def get_forum_topics(followed_topics, forum):
    topics_for_forum = []
    for topic in followed_topics:
        if topic.follow_object.forum == forum.follow_object:
            topics_for_forum.append(topic)
    return topics_for_forum
