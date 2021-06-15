from actstream.models import Follow
from django import template
from django.contrib.contenttypes.models import ContentType

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
    current_follow_object = []
    for obj in object_follows_for_user:
        if obj.follow_object.id == follow_object.id:
            current_follow_object = obj.pk
    return current_follow_object


@register.filter
def get_content_type(follow_object):
    ct = ContentType.objects.get(
        app_label=follow_object._meta.app_label,
        model=follow_object._meta.model_name,
    ).id
    return ct
