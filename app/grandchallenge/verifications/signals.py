from datetime import timedelta

from allauth.account.signals import user_logged_in
from django.conf import settings
from django.core.signing import Signer
from django.db.transaction import on_commit
from django.dispatch import receiver

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
