from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client

from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.challenges.models import Challenge
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload
from tests.factories import UserFactory
from tests.uploads_tests.factories import create_upload_from_file


def get_view_for_user(
    *,
    viewname: str = None,
    challenge: Challenge = None,
    client: Client,
    method: Callable = None,
    user: settings.AUTH_USER_MODEL = None,
    url: str = None,
    reverse_kwargs: dict = None,
    **kwargs,
):
    """Return the view for a particular user."""

    if url is None:
        extra_kwargs = {}

        if challenge:
            extra_kwargs.update({"challenge_short_name": challenge.short_name})

        if reverse_kwargs is not None:
            for key, value in reverse_kwargs.items():
                if value is not None:
                    extra_kwargs.update({key: value})

        url = reverse(viewname, kwargs=extra_kwargs)

    elif viewname:
        raise AttributeError(
            "You defined both a viewname and a url, only use one!"
        )

    if (
        user
        and user.username != settings.ANONYMOUS_USER_NAME
        and not isinstance(user, AnonymousUser)
    ):
        client.force_login(user)

    if method is None:
        method = client.get

    url, kwargs = get_http_host(url=url, kwargs=kwargs)

    try:
        response = method(url, **kwargs)
    finally:
        client.logout()

    return response


def get_http_host(*, url, kwargs):
    """Takes a url and splits out the http host, if found."""
    urlparts = urlparse(url)
    if urlparts[1]:
        kwargs.update({"HTTP_HOST": urlparts[1]})
        url = urlparts[2]
        if urlparts.query:
            url += "?" + urlparts.query
    return url, kwargs


def assert_viewname_status(*, code: int, **kwargs):
    """
    Assert that a viewname for challenge_short_name and pk returns status
    code `code` for a particular user.
    """
    response = get_view_for_user(**kwargs)
    assert response.status_code == code
    return response


def assert_viewname_redirect(*, redirect_url: str, **kwargs):
    """
    Assert that a view redirects to the given url.

    See `assert_viewname_status` for `kwargs` details.
    """
    response = assert_viewname_status(code=302, **kwargs)
    assert list(urlparse(response.url))[2] == redirect_url
    return response


def validate_admin_only_view(*, two_challenge_set, client: Client, **kwargs):
    """
    Assert that a view is only accessible to administrators for that
    particular challenge.
    """

    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_set.challenge_set_1.challenge,
        client=client,
        **kwargs,
    )

    tests = [
        (403, two_challenge_set.challenge_set_1.non_participant),
        (403, two_challenge_set.challenge_set_1.participant),
        (403, two_challenge_set.challenge_set_1.participant1),
        (200, two_challenge_set.challenge_set_1.creator),
        (200, two_challenge_set.challenge_set_1.admin),
        (403, two_challenge_set.challenge_set_2.non_participant),
        (403, two_challenge_set.challenge_set_2.participant),
        (403, two_challenge_set.challenge_set_2.participant1),
        (403, two_challenge_set.challenge_set_2.creator),
        (403, two_challenge_set.challenge_set_2.admin),
        (200, two_challenge_set.admin12),
        (403, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.challenge_set_1.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


def validate_admin_or_participant_view(
    *, two_challenge_set, client: Client, **kwargs
):
    """
    Assert that a view is only accessible to administrators or participants
    of that particular challenge.
    """

    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_set.challenge_set_1.challenge,
        client=client,
        **kwargs,
    )

    tests = [
        (403, two_challenge_set.challenge_set_1.non_participant),
        (200, two_challenge_set.challenge_set_1.participant),
        (200, two_challenge_set.challenge_set_1.participant1),
        (200, two_challenge_set.challenge_set_1.creator),
        (200, two_challenge_set.challenge_set_1.admin),
        (403, two_challenge_set.challenge_set_2.non_participant),
        (403, two_challenge_set.challenge_set_2.participant),
        (403, two_challenge_set.challenge_set_2.participant1),
        (403, two_challenge_set.challenge_set_2.creator),
        (403, two_challenge_set.challenge_set_2.admin),
        (200, two_challenge_set.admin12),
        (200, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.challenge_set_1.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


def validate_open_view(*, challenge_set, client: Client, **kwargs):
    tests = [
        (200, None),
        (200, challenge_set.non_participant),
        (200, challenge_set.participant),
        (200, challenge_set.participant1),
        (200, challenge_set.creator),
        (200, challenge_set.admin),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=challenge_set.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


def validate_logged_in_view(*, challenge_set, client: Client, **kwargs):
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=challenge_set.challenge,
        client=client,
        **kwargs,
    )

    tests = [
        (200, challenge_set.non_participant),
        (200, challenge_set.participant),
        (200, challenge_set.participant1),
        (200, challenge_set.creator),
        (200, challenge_set.admin),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=challenge_set.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


def recurse_callbacks(callbacks, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks() as new_callbacks:
        for callback in callbacks:
            callback()

    if new_callbacks:
        recurse_callbacks(
            callbacks=new_callbacks,
            django_capture_on_commit_callbacks=django_capture_on_commit_callbacks,
        )


def create_raw_upload_image_session(
    *,
    django_capture_on_commit_callbacks,
    image_paths: list[Path],
    user=None,
) -> tuple[RawImageUploadSession, dict[str, UserUpload]]:
    creator = user or UserFactory(email="test@example.com")
    upload_session = RawImageUploadSession.objects.create(creator=creator)

    uploaded_images = {}
    for image in image_paths:
        upload = create_upload_from_file(file_path=image, creator=creator)
        uploaded_images[upload.filename] = upload
        upload_session.user_uploads.add(upload)

    with django_capture_on_commit_callbacks(execute=True):
        upload_session.process_images()

    return upload_session, uploaded_images
