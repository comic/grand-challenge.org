from django import template

register = template.Library()


@register.simple_tag()
def get_first_unread_topic_post_for_user(*, topic, user):
    return topic.get_unread_topic_posts_for_user(user=user).first()
