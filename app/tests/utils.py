from typing import Callable
from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory
from django.views.generic import View

from grandchallenge.challenges.models import Challenge
from grandchallenge.subdomains.utils import reverse
from tests.factories import SUPER_SECURE_TEST_PASSWORD, UserFactory


def assert_redirect(uri: str, *args):
    request, response = assert_status(302, *args)

    redirect_url = list(urlparse(response.url))[2]
    assert uri == redirect_url

    return request, response


def assert_status(
    code: int,
    user: settings.AUTH_USER_MODEL,
    view: View,
    challenge: Challenge,
    rf: RequestFactory,
):
    request = rf.get("/rand")
    request.challenge = challenge

    if user is not None:
        request.user = user

    view = view.as_view()

    if code == 403:
        with pytest.raises(PermissionDenied):
            view(request)
        response = None
    else:
        response = view(request)
        assert response.status_code == code

    return request, response


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

    if user and not isinstance(user, AnonymousUser):
        client.login(
            username=user.username, password=SUPER_SECURE_TEST_PASSWORD
        )

    if method is None:
        method = client.get

    url, kwargs = get_http_host(url=url, kwargs=kwargs)

    try:
        response = method(url, **kwargs)
    finally:
        if user:
            client.logout()

    return response


def get_http_host(*, url, kwargs):
    """Takes a url and splits out the http host, if found."""
    urlparts = urlparse(url)
    if urlparts[1]:
        kwargs.update({"HTTP_HOST": urlparts[1]})
        url = urlparts[2]
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


def validate_staff_only_view(
    *, client: Client, should_redirect=False, **kwargs
):
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL, client=client, **kwargs
    )

    user = UserFactory()
    staff_user = UserFactory(is_staff=True)

    assert_viewname_status(code=403, client=client, user=user, **kwargs)

    if should_redirect:
        staff_response = assert_viewname_status(
            code=302, client=client, user=staff_user, **kwargs
        )
        assert settings.LOGIN_URL not in staff_response.url
    else:
        assert_viewname_status(
            code=200, client=client, user=staff_user, **kwargs
        )


def validate_admin_only_text_in_page(
    *, expected_text, two_challenge_set, client: Client, **kwargs
):
    tests = [
        (False, None),
        (False, two_challenge_set.challenge_set_1.non_participant),
        (False, two_challenge_set.challenge_set_1.participant),
        (False, two_challenge_set.challenge_set_1.participant1),
        (True, two_challenge_set.challenge_set_1.creator),
        (True, two_challenge_set.challenge_set_1.admin),
        (False, two_challenge_set.challenge_set_2.non_participant),
        (False, two_challenge_set.challenge_set_2.participant),
        (False, two_challenge_set.challenge_set_2.participant1),
        (False, two_challenge_set.challenge_set_2.creator),
        (False, two_challenge_set.challenge_set_2.admin),
        (True, two_challenge_set.admin12),
        (False, two_challenge_set.participant12),
        (True, two_challenge_set.admin1participant2),
    ]

    for test in tests:
        response = assert_viewname_status(
            code=200,
            challenge=two_challenge_set.challenge_set_1.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )
        assert (expected_text in str(response.content)) == test[0]
