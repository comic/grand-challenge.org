from django import template

from grandchallenge.discussion_forums.models import PostReadRecord

register = template.Library()


@register.simple_tag()
def get_first_unread_post_for_user(*, topic, user):
    unread_posts = topic.get_unread_posts_for_user(user=user)
    return unread_posts[0] if unread_posts else None


@register.simple_tag()
def post_unread_by_user(*, post, user):
    return not PostReadRecord.objects.filter(user=user, post=post).exists()
