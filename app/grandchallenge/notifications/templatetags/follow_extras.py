from actstream.models import Follow
from django import template
from django.contrib.contenttypes.models import ContentType

from grandchallenge.notifications.forms import FollowForm

register = template.Library()


@register.simple_tag
def get_follow_object_pk(user, follow_object):
    object_follows_for_user = Follow.objects.filter(
        user=user,
        content_type=ContentType.objects.get(
            app_label=follow_object._meta.app_label,
            model=follow_object._meta.model_name,
        ),
    ).all()

    if not object_follows_for_user:
        current_follow_object = []
    else:
        current_follow_object = []
        for obj in object_follows_for_user:
            if not obj.follow_object:
                continue
            elif obj.follow_object.id == follow_object.id:
                current_follow_object = obj.pk
    return current_follow_object


@register.simple_tag
def follow_form(*, user, follow_object):
    return FollowForm(user=user, follow_object=follow_object)


@register.simple_tag()
def is_participant(user, challenge):
    if challenge.is_participant(user):
        return True
