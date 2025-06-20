from django import template

register = template.Library()


@register.simple_tag()
def check_unread_topic_posts_for_user(*, topic):
    # for this to work, you need to prefetch the TopicReadRecords for the user in the view
    record = next(
        (r for r in topic.user_read_records if r.topic_id == topic.id),
        None,
    )

    if record is None:
        return True

    return topic.last_post.created >= record.modified
