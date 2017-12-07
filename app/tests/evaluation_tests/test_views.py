from typing import Callable
from urllib.parse import urlparse

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client

from comicmodels.models import ComicSite
from comicsite.core.urlresolvers import reverse
from tests.factories import SUPER_SECURE_TEST_PASSWORD


def assert_viewname_status(*,
                           code: int,
                           viewname: str,
                           challenge: ComicSite,
                           client: Client,
                           method: Callable,
                           pk: str = None,
                           user: settings.AUTH_USER_MODEL = None):

    kwargs = {'challenge_short_name': challenge.short_name}

    if pk:
        kwargs['pk'] = pk

    url = reverse(viewname, kwargs=kwargs)


    if user and not isinstance(user, AnonymousUser):
        client.login(username=user.username,
                     password=SUPER_SECURE_TEST_PASSWORD)

    response = method(url)

    if user:
        client.logout()

    assert response.status_code == code
    return response


def assert_viewname_redirect(*,
                             url: str,
                             **kwargs):
    response = assert_viewname_status(code=302, **kwargs)
    redirect_url = list(urlparse(response.url))[2]
    assert url == redirect_url
    return response


def validate_admin_only_view(*,
                             challenge_set,
                             client: Client,
                             **kwargs):
    # No user
    assert_viewname_redirect(url=settings.LOGIN_URL,
                             challenge=challenge_set.challenge,
                             client=client,
                             method=client.get,
                             **kwargs)

    tests = [
        (403, challenge_set.non_participant),
        (403, challenge_set.participant),
        (403, challenge_set.participant1),
        (200, challenge_set.creator),
        (200, challenge_set.admin)
    ]

    for test in tests:
        assert_viewname_status(code=test[0],
                               challenge=challenge_set.challenge,
                               method=client.get,
                               client=client,
                               user=test[1],
                               **kwargs)


def validate_admin_or_participant_view(*,
                                       challenge_set,
                                       client: Client,
                                       **kwargs):
    # No user
    assert_viewname_redirect(url=settings.LOGIN_URL,
                             challenge=challenge_set.challenge,
                             client=client,
                             method=client.get,
                             **kwargs)

    tests = [
        (403, challenge_set.non_participant),
        (200, challenge_set.participant),
        (200, challenge_set.participant1),
        (200, challenge_set.creator),
        (200, challenge_set.admin)
    ]

    for test in tests:
        assert_viewname_status(code=test[0],
                               challenge=challenge_set.challenge,
                               method=client.get,
                               client=client,
                               user=test[1],
                               **kwargs)


def validate_open_view(*,
                       challenge_set,
                       client: Client,
                       **kwargs):
    tests = [
        (200, None),
        (200, challenge_set.non_participant),
        (200, challenge_set.participant),
        (200, challenge_set.participant1),
        (200, challenge_set.creator),
        (200, challenge_set.admin)
    ]

    for test in tests:
        assert_viewname_status(code=test[0],
                               challenge=challenge_set.challenge,
                               method=client.get,
                               client=client,
                               user=test[1],
                               **kwargs)


@pytest.mark.django_db
def test_manage(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:manage',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_method_list(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:method-list',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_method_create(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:method-create',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)

@pytest.mark.django_db
def test_method_detail(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:method-detail',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             pk=EvalChallengeSet.method.pk,
                             client=client)

@pytest.mark.django_db
def test_submission_list(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:submission-list',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_submission_create(client, EvalChallengeSet):
    validate_admin_or_participant_view(viewname='evaluation:submission-create',
                                       challenge_set=EvalChallengeSet.ChallengeSet,
                                       client=client)

# TODO: we need a submission to test
@pytest.mark.skip
@pytest.mark.django_db
def test_submission_detail(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:submission-detail',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_job_list(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:job-list',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_job_create(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:job-create',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)

# TODO: we need a job to test
@pytest.mark.skip
@pytest.mark.django_db
def test_job_detail(client, EvalChallengeSet):
    validate_admin_only_view(viewname='evaluation:job-detail',
                             challenge_set=EvalChallengeSet.ChallengeSet,
                             client=client)


@pytest.mark.django_db
def test_result_list(client, EvalChallengeSet):
    validate_open_view(viewname='evaluation:result-list',
                       challenge_set=EvalChallengeSet.ChallengeSet,
                       client=client)

# TODO: we need a result to test
@pytest.mark.skip
@pytest.mark.django_db
def test_result_detail(client, EvalChallengeSet):
    validate_open_view(viewname='evaluation:result-detail',
                       challenge_set=EvalChallengeSet.ChallengeSet,
                       client=client)
