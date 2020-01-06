from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail

from grandchallenge.core.utils.email import send_templated_email
from grandchallenge.evaluation.templatetags.evaluation_extras import user_error


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


def send_failed_job_email(job):
    algorithm = job.algorithm_image.algorithm
    message = (
        f"Unfortunately your job for algorithm "
        f"'{algorithm.title}' failed with an error. "
        f"The error message is:\n\n"
        f"{user_error(job.output)}\n\n"
        f"You may wish to try and correct this, or contact the challenge "
        f"organizers. The following information may help them:\n"
        f"User: {job.creator.username}\n"
        f"Job ID: {job.pk}\n"
        f"Submission ID: {job.pk}"
    )
    recipient_emails = [
        o.email for o in algorithm.editors_group.user_set.all()
    ]
    recipient_emails.append(job.creator.email)

    for email in {*recipient_emails}:
        send_mail(
            subject=(
                f"[{Site.objects.get_current().domain.lower()}] "
                f"[{algorithm.title.lower()}] "
                f"Job Failed"
            ),
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
