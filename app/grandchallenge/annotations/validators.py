from django.conf import settings
from rest_framework import serializers


def validate_grader_is_current_retina_user(grader, context):
    """
    Check if the passed grader is the request.user that is passed in the context.

    Only applies to users that are in the retina_graders group.
    BEWARE! Validation will pass if user is not logged in or request or
    request.user is not defined.
    """
    request = context.get("request")
    if (
        request is not None
        and request.user is not None
        and request.user.is_authenticated
    ):
        user = request.user
        if user.groups.filter(
            name=settings.RETINA_GRADERS_GROUP_NAME
        ).exists():
            if grader != user:
                raise serializers.ValidationError(
                    "User is not allowed to create annotation for other grader"
                )
