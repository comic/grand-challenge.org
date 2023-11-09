from django import template
from django.conf import settings

register = template.Library()


@register.filter
def is_challenge_reviewer(user):
    """
    Checks if the user is in the challenge request reviewer group
    :param user: Django User model
    :return: true/false
    """
    return user.groups.filter(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    ).exists()
