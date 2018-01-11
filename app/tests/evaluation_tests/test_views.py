from collections import namedtuple
from typing import Callable
from urllib.parse import urlparse

import factory
import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db.models import signals
from django.test import Client

from comicmodels.models import ComicSite
from comicsite.core.urlresolvers import reverse
from tests.factories import SUPER_SECURE_TEST_PASSWORD, MethodFactory, \
    SubmissionFactory, JobFactory, ResultFactory


# TODO: Test creation with forms.

def submission_and_job(*, challenge, creator):
    """ Creates a submission and a job for that submission """
    s = SubmissionFactory(challenge=challenge, creator=creator)
    j = JobFactory(submission=s)
    return s, j


@pytest.fixture()
def submissions_and_jobs(two_challenge_sets):
    """ Creates jobs (j) and submissions (s) for each participant (p) and
    challenge (c).  """
    SubmissionsAndJobs = namedtuple('SubmissionsAndJobs',
                                    ['p_s1',
                                     'p_s2',
                                     'p1_s1',
                                     'p12_s1_c1',
                                     'p12_s1_c2',
                                     'j_p_s1',
                                     'j_p_s2',
                                     'j_p1_s1',
                                     'j_p12_s1_c1',
                                     'j_p12_s1_c2',
                                     ])

    # participant 0, submission 1, challenge 1, etc
    p_s1, j_p_s1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant)
    p_s2, j_p_s2 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant)
    p1_s1, j_p1_s1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant1)

    # participant12, submission 1 to each challenge
    p12_s1_c1, j_p12_s1_c1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.participant12)
    p12_s1_c2, j_p12_s1_c2 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet2.challenge,
        creator=two_challenge_sets.participant12)

    return SubmissionsAndJobs(p_s1, p_s2, p1_s1, p12_s1_c1, p12_s1_c2,
                              j_p_s1, j_p_s2, j_p1_s1, j_p12_s1_c1,
                              j_p12_s1_c2)


def get_view_for_user(*,
                      viewname: str,
                      challenge: ComicSite,
                      client: Client,
                      method: Callable,
                      pk: str = None,
                      user: settings.AUTH_USER_MODEL = None):
    """ Returns the view for a particular user """
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

    return response


def assert_viewname_status(*, code: int, **kwargs):
    """ Asserts that a viewname for challenge_short_name and pk returns status
    code `code` for a particular user """

    response = get_view_for_user(**kwargs)

    assert response.status_code == code
    return response


def assert_viewname_redirect(*,
                             url: str,
                             **kwargs):
    """ Asserts that a view redirects to the given url. See
    assert_viewname_status for kwargs details """
    response = assert_viewname_status(code=302, **kwargs)
    redirect_url = list(urlparse(response.url))[2]
    assert url == redirect_url
    return response


def validate_admin_only_view(*,
                             two_challenge_set,
                             client: Client,
                             **kwargs):
    """ Assert that a view is only accessible to administrators for that
    particular challenge """
    # No user
    assert_viewname_redirect(
        url=settings.LOGIN_URL,
        challenge=two_challenge_set.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        **kwargs
    )

    tests = [
        (403, two_challenge_set.ChallengeSet1.non_participant),
        (403, two_challenge_set.ChallengeSet1.participant),
        (403, two_challenge_set.ChallengeSet1.participant1),
        (200, two_challenge_set.ChallengeSet1.creator),
        (200, two_challenge_set.ChallengeSet1.admin),
        (403, two_challenge_set.ChallengeSet2.non_participant),
        (403, two_challenge_set.ChallengeSet2.participant),
        (403, two_challenge_set.ChallengeSet2.participant1),
        (403, two_challenge_set.ChallengeSet2.creator),
        (403, two_challenge_set.ChallengeSet2.admin),
        (200, two_challenge_set.admin12),
        (403, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.ChallengeSet1.challenge,
            method=client.get,
            client=client,
            user=test[1],
            **kwargs
        )


def validate_admin_or_participant_view(*,
                                       two_challenge_set,
                                       client: Client,
                                       **kwargs):
    """ Assert that a view is only accessible to administrators or participants
    of that particular challenge """
    # No user
    assert_viewname_redirect(
        url=settings.LOGIN_URL,
        challenge=two_challenge_set.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        **kwargs
    )

    tests = [
        (403, two_challenge_set.ChallengeSet1.non_participant),
        (200, two_challenge_set.ChallengeSet1.participant),
        (200, two_challenge_set.ChallengeSet1.participant1),
        (200, two_challenge_set.ChallengeSet1.creator),
        (200, two_challenge_set.ChallengeSet1.admin),
        (403, two_challenge_set.ChallengeSet2.non_participant),
        (403, two_challenge_set.ChallengeSet2.participant),
        (403, two_challenge_set.ChallengeSet2.participant1),
        (403, two_challenge_set.ChallengeSet2.creator),
        (403, two_challenge_set.ChallengeSet2.admin),
        (200, two_challenge_set.admin12),
        (200, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]

    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.ChallengeSet1.challenge,
            method=client.get,
            client=client,
            user=test[1],
            **kwargs
        )


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
def test_manage(client, TwoChallengeSets):
    validate_admin_only_view(viewname='evaluation:manage',
                             two_challenge_set=TwoChallengeSets,
                             client=client)


@pytest.mark.django_db
def test_method_list(client, TwoChallengeSets):
    validate_admin_only_view(viewname='evaluation:method-list',
                             two_challenge_set=TwoChallengeSets,
                             client=client)


@pytest.mark.django_db
def test_method_create(client, TwoChallengeSets):
    validate_admin_only_view(viewname='evaluation:method-create',
                             two_challenge_set=TwoChallengeSets,
                             client=client)


@pytest.mark.django_db
def test_method_detail(client, TwoChallengeSets):
    method = MethodFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                           creator=TwoChallengeSets.ChallengeSet1.admin)

    validate_admin_only_view(viewname='evaluation:method-detail',
                             two_challenge_set=TwoChallengeSets,
                             pk=method.pk,
                             client=client)


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_list(client, TwoChallengeSets):
    validate_admin_or_participant_view(viewname='evaluation:submission-list',
                                       two_challenge_set=TwoChallengeSets,
                                       client=client)

    p_s1, p_s2, p1_s1, p12_s1_c1, p12_s1_c2, *_ = submissions_and_jobs(
        TwoChallengeSets)

    # Participants should only be able to see their own submissions
    response = get_view_for_user(
        viewname='evaluation:submission-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.ChallengeSet1.participant)
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content
    assert str(p12_s1_c1.pk) not in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content

    # Admins should be able to see all submissions
    response = get_view_for_user(
        viewname='evaluation:submission-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.ChallengeSet1.admin)
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) in response.rendered_content
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content

    # Only submissions relevant to this challenge should be listed
    response = get_view_for_user(
        viewname='evaluation:submission-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.participant12)
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    assert str(p_s1.pk) not in response.rendered_content
    assert str(p_s2.pk) not in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_submission_create(client, TwoChallengeSets):
    validate_admin_or_participant_view(viewname='evaluation:submission-create',
                                       two_challenge_set=TwoChallengeSets,
                                       client=client)


@pytest.mark.django_db
def test_submission_detail(client, TwoChallengeSets):
    submission = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant)

    validate_admin_only_view(viewname='evaluation:submission-detail',
                             two_challenge_set=TwoChallengeSets,
                             pk=submission.pk,
                             client=client)


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_job_list(client, TwoChallengeSets):
    validate_admin_or_participant_view(viewname='evaluation:job-list',
                                       two_challenge_set=TwoChallengeSets,
                                       client=client)

    *_, j_p_s1, j_p_s2, j_p1_s1, j_p12_s1_c1, j_p12_s1_c2 = submissions_and_jobs(
        TwoChallengeSets)

    # Participants should only be able to see their own jobs
    response = get_view_for_user(
        viewname='evaluation:job-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.ChallengeSet1.participant)
    assert str(j_p_s1.pk) in response.rendered_content
    assert str(j_p_s2.pk) in response.rendered_content
    assert str(j_p1_s1.pk) not in response.rendered_content
    assert str(j_p12_s1_c1.pk) not in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content

    # Admins should be able to see all jobs
    response = get_view_for_user(
        viewname='evaluation:job-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.ChallengeSet1.admin)
    assert str(j_p_s1.pk) in response.rendered_content
    assert str(j_p_s2.pk) in response.rendered_content
    assert str(j_p1_s1.pk) in response.rendered_content
    assert str(j_p12_s1_c1.pk) in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content

    # Only jobs relevant to this challenge should be listed
    response = get_view_for_user(
        viewname='evaluation:job-list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.get,
        user=TwoChallengeSets.participant12)
    assert str(j_p12_s1_c1.pk) in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content
    assert str(j_p_s1.pk) not in response.rendered_content
    assert str(j_p_s2.pk) not in response.rendered_content
    assert str(j_p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_job_create(client, TwoChallengeSets):
    validate_admin_only_view(viewname='evaluation:job-create',
                             two_challenge_set=TwoChallengeSets,
                             client=client)


@pytest.mark.django_db
def test_job_detail(client, TwoChallengeSets):
    method = MethodFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                           creator=TwoChallengeSets.ChallengeSet1.admin,
                           ready=True)

    submission = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant)

    job = JobFactory(method=method, submission=submission)

    validate_admin_only_view(viewname='evaluation:job-detail',
                             two_challenge_set=TwoChallengeSets,
                             pk=job.pk,
                             client=client)


@pytest.mark.django_db
def test_result_list(client, EvalChallengeSet):
    validate_open_view(viewname='evaluation:result-list',
                       challenge_set=EvalChallengeSet.ChallengeSet,
                       client=client)
    # TODO: test that private results cannot be seen


@pytest.mark.django_db
def test_result_detail(client, EvalChallengeSet):
    result = ResultFactory(challenge=EvalChallengeSet.ChallengeSet.challenge)

    validate_open_view(viewname='evaluation:result-detail',
                       challenge_set=EvalChallengeSet.ChallengeSet,
                       pk=result.pk,
                       client=client)
