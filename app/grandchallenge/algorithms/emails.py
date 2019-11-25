from django.contrib.sites.models import Site

from grandchallenge.core.utils.email import send_templated_email


def send_permission_request_email(obj):
    """
    Emails the editors that someone has requested to view an algorithm.

    Parameters
    ----------
    obj:
        AlgorithmPermissionRequest object containing info on which
        user requested access to which algorithm.
    """
    title = f"[{obj.algorithm.title}] New access request"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "algorithm": obj.algorithm,
    }
    for editor in obj.algorithm.editors_group.user_set.all():
        kwargs["editor"] = editor
        send_templated_email(
            title,
            "algorithms/emails/access_request.html",
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
        user requested access to which algorithm.
    """
    title = f"[{obj.algorithm.title}] Access granted"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "algorithm": obj.algorithm,
    }
    send_templated_email(
        title,
        "algorithms/emails/access_granted.html",
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
    title = f"[{obj.algorithm.title}] Access denied"
    kwargs = {
        "user": obj.user,
        "site": Site.objects.get_current(),
        "algorithm": obj.algorithm,
        "permission_request": obj,
    }
    send_templated_email(
        title,
        "algorithms/emails/access_denied.html",
        kwargs,
        [obj.user.email],
    )
