from django import template
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.discussion_forums.models import TopicReadRecord

register = template.Library()


@register.simple_tag()
def check_unread_topic_posts_for_user(*, topic, user):
    try:
        record = TopicReadRecord.objects.get(user=user, topic=topic)
        if topic.last_post.created >= record.modified:
            return True
        else:
            return False
    except ObjectDoesNotExist:
        return True
