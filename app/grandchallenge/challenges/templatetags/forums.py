from typing import Union

from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from machina.apps.forum.models import Forum

register = template.Library()


@register.filter
def forum_link(forum: Union[Forum, None]) -> str:

    if forum.challenge and forum.challenge.logo:
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
        challenge_logo = ""

    return format_html(
        '<span class="text-nowrap"><a href="{0}">{1}</a>&nbsp;&nbsp;<a href="{0}">{2}</a></span>',
        forum_url,
        challenge_logo,
        forum_name,
    )


@register.simple_tag
def get_forum_specific_topic_follows(topic_follows, forum):
    topic_follows_for_forum = []
    for follow in topic_follows:
        if follow.follow_object.forum == forum:
            topic_follows_for_forum.append(follow)
    return topic_follows_for_forum


@register.filter
def get_forums(topic_follows):
    forums = []
    for follow in topic_follows:
        if follow.follow_object.forum not in forums:
            forums.append(follow.follow_object.forum)
    return forums


@register.simple_tag()
def subset_by_content_type(queryset, content_type, content_type_app_label):
    filtered_qs = queryset.filter(
        content_type=ContentType.objects.get(
            app_label=content_type_app_label, model=content_type
        ).id
    )
    return filtered_qs
