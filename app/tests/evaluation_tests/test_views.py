from collections import namedtuple
from datetime import timedelta

import factory
import pytest
from django.db.models import signals
from django.utils import timezone

from tests.factories import (
    MethodFactory,
    SubmissionFactory,
    JobFactory,
    ResultFactory,
)

# TODO: Test creation with forms.
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_admin_or_participant_view,
    validate_open_view,
)


def submission_and_job(*, challenge, creator):
    """ Creates a submission and a job for that submission """
    s = SubmissionFactory(challenge=challenge, creator=creator)
    j = JobFactory(submission=s)
    return s, j


def submissions_and_jobs(two_challenge_sets):
    """ Creates jobs (j) and submissions (s) for each participant (p) and
    challenge (c).  """
    SubmissionsAndJobs = namedtuple(
        "SubmissionsAndJobs",
        [
            "p_s1",
            "p_s2",
            "p1_s1",
            "p12_s1_c1",
            "p12_s1_c2",
            "j_p_s1",
            "j_p_s2",
            "j_p1_s1",
            "j_p12_s1_c1",
            "j_p12_s1_c2",
        ],
    )
    # participant 0, submission 1, challenge 1, etc
    p_s1, j_p_s1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant,
    )
    p_s2, j_p_s2 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant,
    )
    p1_s1, j_p1_s1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.ChallengeSet1.participant1,
    )
    # participant12, submission 1 to each challenge
    p12_s1_c1, j_p12_s1_c1 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet1.challenge,
        creator=two_challenge_sets.participant12,
    )
    p12_s1_c2, j_p12_s1_c2 = submission_and_job(
        challenge=two_challenge_sets.ChallengeSet2.challenge,
        creator=two_challenge_sets.participant12,
    )
    return SubmissionsAndJobs(
        p_s1,
        p_s2,
        p1_s1,
        p12_s1_c1,
        p12_s1_c2,
        j_p_s1,
        j_p_s2,
        j_p1_s1,
        j_p12_s1_c1,
        j_p12_s1_c2,
    )


@pytest.mark.django_db
def test_method_list(client, TwoChallengeSets):
    validate_admin_only_view(
        viewname="evaluation:method-list",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_method_create(client, TwoChallengeSets):
    validate_admin_only_view(
        viewname="evaluation:method-create",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_method_detail(client, TwoChallengeSets):
    method = MethodFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.admin,
    )
    validate_admin_only_view(
        viewname="evaluation:method-detail",
        two_challenge_set=TwoChallengeSets,
        reverse_kwargs={"pk": method.pk},
        client=client,
    )


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_list(client, TwoChallengeSets):
    validate_admin_or_participant_view(
        viewname="evaluation:submission-list",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )
    p_s1, p_s2, p1_s1, p12_s1_c1, p12_s1_c2, *_ = submissions_and_jobs(
        TwoChallengeSets
    )
    # Participants should only be able to see their own submissions
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.ChallengeSet1.participant,
    )
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content
    assert str(p12_s1_c1.pk) not in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    # Admins should be able to see all submissions
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.ChallengeSet1.admin,
    )
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) in response.rendered_content
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    # Only submissions relevant to this challenge should be listed
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.participant12,
    )
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    assert str(p_s1.pk) not in response.rendered_content
    assert str(p_s2.pk) not in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_submission_create(client, TwoChallengeSets):
    validate_admin_or_participant_view(
        viewname="evaluation:submission-create",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )

    response = get_view_for_user(
        viewname="evaluation:submission-create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.ChallengeSet1.participant,
        client=client,
    )

    assert response.status_code == 200
    assert "Creator" not in response.rendered_content


@pytest.mark.django_db
def test_legacy_submission_create(client, TwoChallengeSets):
    validate_admin_only_view(
        viewname="evaluation:submission-create-legacy",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )

    response = get_view_for_user(
        viewname="evaluation:submission-create-legacy",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12,
        client=client,
    )

    assert response.status_code == 200
    assert "Creator" in response.rendered_content


@pytest.mark.django_db
def test_submission_time_limit(client, TwoChallengeSets):
    SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )

    def get_submission_view():
        return get_view_for_user(
            viewname="evaluation:submission-create",
            challenge=TwoChallengeSets.ChallengeSet1.challenge,
            client=client,
            user=TwoChallengeSets.ChallengeSet1.participant,
        )

    assert "make 9 more" in get_submission_view().rendered_content
    s = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )
    s.created = timezone.now() - timedelta(hours=23)
    s.save()
    assert "make 8 more" in get_submission_view().rendered_content
    s = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )
    s.created = timezone.now() - timedelta(hours=25)
    s.save()
    assert "make 8 more" in get_submission_view().rendered_content


@pytest.mark.django_db
def test_submission_detail(client, TwoChallengeSets):
    submission = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )
    validate_admin_only_view(
        viewname="evaluation:submission-detail",
        two_challenge_set=TwoChallengeSets,
        reverse_kwargs={"pk": submission.pk},
        client=client,
    )


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_job_list(client, TwoChallengeSets):
    validate_admin_or_participant_view(
        viewname="evaluation:job-list",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )
    *_, j_p_s1, j_p_s2, j_p1_s1, j_p12_s1_c1, j_p12_s1_c2 = submissions_and_jobs(
        TwoChallengeSets
    )
    # Participants should only be able to see their own jobs
    response = get_view_for_user(
        viewname="evaluation:job-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.ChallengeSet1.participant,
    )
    assert str(j_p_s1.pk) in response.rendered_content
    assert str(j_p_s2.pk) in response.rendered_content
    assert str(j_p1_s1.pk) not in response.rendered_content
    assert str(j_p12_s1_c1.pk) not in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content
    # Admins should be able to see all jobs
    response = get_view_for_user(
        viewname="evaluation:job-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.ChallengeSet1.admin,
    )
    assert str(j_p_s1.pk) in response.rendered_content
    assert str(j_p_s2.pk) in response.rendered_content
    assert str(j_p1_s1.pk) in response.rendered_content
    assert str(j_p12_s1_c1.pk) in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content
    # Only jobs relevant to this challenge should be listed
    response = get_view_for_user(
        viewname="evaluation:job-list",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.participant12,
    )
    assert str(j_p12_s1_c1.pk) in response.rendered_content
    assert str(j_p12_s1_c2.pk) not in response.rendered_content
    assert str(j_p_s1.pk) not in response.rendered_content
    assert str(j_p_s2.pk) not in response.rendered_content
    assert str(j_p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_job_create(client, TwoChallengeSets):
    validate_admin_only_view(
        viewname="evaluation:job-create",
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_job_detail(client, TwoChallengeSets):
    method = MethodFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.admin,
        ready=True,
    )
    submission = SubmissionFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        creator=TwoChallengeSets.ChallengeSet1.participant,
    )
    job = JobFactory(method=method, submission=submission)
    validate_admin_only_view(
        viewname="evaluation:job-detail",
        two_challenge_set=TwoChallengeSets,
        reverse_kwargs={"pk": job.pk},
        client=client,
    )


@pytest.mark.django_db
def test_result_list(client, EvalChallengeSet):
    validate_open_view(
        viewname="evaluation:result-list",
        challenge_set=EvalChallengeSet.ChallengeSet,
        client=client,
    )


# TODO: test that private results cannot be seen
@pytest.mark.django_db
def test_result_detail(client, EvalChallengeSet):
    submission = SubmissionFactory(
        challenge=EvalChallengeSet.ChallengeSet.challenge,
        creator=EvalChallengeSet.ChallengeSet.participant,
    )
    job = JobFactory(submission=submission)
    result = ResultFactory(job=job)
    validate_open_view(
        viewname="evaluation:result-detail",
        challenge_set=EvalChallengeSet.ChallengeSet,
        reverse_kwargs={"pk": result.pk},
        client=client,
    )
