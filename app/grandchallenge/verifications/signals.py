from allauth.account.signals import user_logged_in
from django.conf import settings
from django.core.signing import Signer
from django.db.transaction import on_commit
from django.dispatch import receiver

from grandchallenge.verifications.tasks import update_verification_user_set


@receiver(user_logged_in)
def handle_user_logged_in(*, request, user, response, **_):
    cookie = request.COOKIES.get(settings.VERIFICATIONS_USER_SET_COOKIE_NAME)
    signer = Signer()

    if cookie is None:
        response.set_cookie(
            settings.VERIFICATIONS_USER_SET_COOKIE_NAME,
            signer.sign_object([user.username]),
        )
    else:
        usernames = {*signer.unsign_object(cookie)}
        usernames.add(user.username)
        response.set_cookie(
            settings.VERIFICATIONS_USER_SET_COOKIE_NAME,
            signer.sign_object([*usernames]),
        )

        if len(usernames) > 1:
            on_commit(
                update_verification_user_set.signature(
                    kwargs={"usernames": [*usernames]}
                ).apply_async
            )
