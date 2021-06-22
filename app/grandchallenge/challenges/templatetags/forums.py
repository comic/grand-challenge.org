from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()


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
