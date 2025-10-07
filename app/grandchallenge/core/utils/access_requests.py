from actstream.actions import follow
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _

from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)


class AccessRequestHandlingOptions(models.TextChoices):
    """
    Options for handling access requests to archives, algorithms, challenges
    and reader studies.
    """

    MANUAL_REVIEW = "MANUAL_REVIEW", _("Manually review all requests")
    ACCEPT_VERIFIED_USERS = (
        "ACCEPT_VERIFIED_USERS",
        _("Automatically accept requests from verified users only"),
    )
    ACCEPT_ALL = (
        "ACCEPT_ALL",
        _("Automatically accept requests from all users"),
    )


def process_access_request(request_object):
    if (
        request_object.base_object.access_request_handling
        == AccessRequestHandlingOptions.ACCEPT_ALL
    ):
        # immediately allow access, no need for a notification
        request_object.status = request_object.ACCEPTED
        request_object.save()
        return
    elif (
        request_object.base_object.access_request_handling
        == AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS
    ):
        try:
            if request_object.user.verification.is_verified:
                # immediately allow access, no need for a notification
                request_object.status = request_object.ACCEPTED
                request_object.save()
                return
        except ObjectDoesNotExist:
            pass

    follow(
        user=request_object.user,
        obj=request_object,
        actor_only=False,
        send_action=False,
    )
    Notification.send(
        kind=NotificationTypeChoices.ACCESS_REQUEST,
        message="requested access to",
        actor=request_object.user,
        target=request_object.base_object,
    )
