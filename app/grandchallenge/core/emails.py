from django.contrib.sites.models import Site

from grandchallenge.core.utils.email import send_templated_email


def send_permission_request_email(obj):
    """
    Emails the editors that someone has requested to view an algorithm.

    Parameters
    ----------
    obj:
        AlgorithmPermissionRequest object containing info on which
        user requested access to which base_object.
    """
    title = f"[{obj.object_name}] New access request"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "base_object": obj.base_object,
        "permission_list_url": obj.permission_list_url,
    }
    for editor in obj.base_object.editors_group.user_set.all():
        kwargs["editor"] = editor
        send_templated_email(
            title,
            "grandchallenge/emails/access_request.html",
            kwargs,
            [editor.email],
        )


def send_permission_granted_email(obj):
    """
    Emails the requester that their request has been approved.

    Parameters
    ----------
    obj:
        AlgorithmPermissionRequest object containing info on which
        user requested access to which base_object.
    """
    title = f"[{obj.object_name}] Access granted"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "base_object": obj.base_object,
    }
    send_templated_email(
        title,
        "grandchallenge/emails/access_granted.html",
        kwargs,
        [obj.user.email],
    )


def send_permission_denied_email(obj):
    """
    Emails the requester that their request has been approved.

    Parameters
    ----------
    obj:
        AlgorithmPermissionRequest object containing info on which
        user requested access to which algorithm and optionally the
        reason for rejection.
    """
    title = f"[{obj.object_name}] Access denied"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "base_object": obj.base_object,
        "permission_request": obj,
    }
    send_templated_email(
        title,
        "grandchallenge/emails/access_denied.html",
        kwargs,
        [obj.user.email],
    )
