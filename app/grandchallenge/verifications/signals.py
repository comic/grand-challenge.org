from datetime import timedelta

from allauth.account.signals import user_logged_in
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import mail_managers
from django.core.signing import Signer
from django.db.models.signals import m2m_changed
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import format_html

from grandchallenge.profiles.tasks import deactivate_user
from grandchallenge.verifications.models import VerificationUserSet
from grandchallenge.verifications.tasks import update_verification_user_set


def set_verification_user_set_cookie(*, response, usernames):
    response.set_cookie(
        key=settings.VERIFICATIONS_USER_SET_COOKIE_NAME,
        value=Signer().sign_object(usernames),
        max_age=timedelta(days=28),
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="Strict",
    )


@receiver(user_logged_in)
def handle_user_logged_in(*, request, user, response, **_):
    try:
        cookie = request.COOKIES[settings.VERIFICATIONS_USER_SET_COOKIE_NAME]
    except KeyError:
        set_verification_user_set_cookie(
            response=response, usernames=[user.username]
        )
    else:
        usernames = {*Signer().unsign_object(cookie)}
        usernames.add(user.username)
        set_verification_user_set_cookie(
            response=response, usernames=[*usernames]
        )

        if len(usernames) > 1:
            on_commit(
                update_verification_user_set.signature(
                    kwargs={"usernames": [*usernames]}
                ).apply_async
            )


@receiver(m2m_changed, sender=VerificationUserSet.users.through)
def auto_disable_user_in_verification_user_set(
    *, instance, action, reverse, pk_set, **__
):
    if action != "post_add":
        return

    if reverse:
        verification_user_sets = VerificationUserSet.objects.filter(
            pk__in=pk_set
        )
        users = [instance]
    else:
        verification_user_sets = [instance]
        users = get_user_model().objects.filter(pk__in=pk_set)

    for verification_user_set in verification_user_sets:

        verification_user_set.modified = timezone.now()
        verification_user_set.save()

        if (
            not verification_user_set.is_false_positive
            and verification_user_set.auto_deactivate
        ):
            for user in users:
                on_commit(
                    deactivate_user.signature(
                        kwargs={"user_pk": user.pk}
                    ).apply_async
                )
                mail_managers(
                    subject="User automatically deactivated",
                    message=format_html(
                        (
                            "User '{username}' was deactivated after being added to a "
                            "verification user set with auto disable enabled.\n\n"
                            "See:\n{vus_link}"
                        ),
                        username=user.username,
                        vus_link=verification_user_set.get_absolute_url(),
                    ),
                )
