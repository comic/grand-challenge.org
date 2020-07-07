from collections import namedtuple
from datetime import timedelta

import factory
import pytest
from django.db.models import signals
from django.utils import timezone

from tests.factories import (
    EvaluationFactory,
    MethodFactory,
    SubmissionFactory,
)
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_admin_or_participant_view,
    validate_open_view,
)


def submission_and_evaluation(*, challenge, creator):
    """Creates a submission and an evaluation for that submission."""
    s = SubmissionFactory(challenge=challenge, creator=creator)
    e = EvaluationFactory(submission=s)
    return s, e


def submissions_and_evaluations(two_challenge_sets):
    """
    Create (e)valuations and (s)ubmissions for each (p)articipant and
    (c)hallenge.
    """
    SubmissionsAndEvaluations = namedtuple(
        "SubmissionsAndEvaluations",
        [
            "p_s1",
            "p_s2",
            "p1_s1",
            "p12_s1_c1",
            "p12_s1_c2",
            "e_p_s1",
            "e_p_s2",
            "e_p1_s1",
            "e_p12_s1_c1",
            "e_p12_s1_c2",
        ],
    )
    # participant 0, submission 1, challenge 1, etc
    p_s1, e_p_s1 = submission_and_evaluation(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )
    p_s2, e_p_s2 = submission_and_evaluation(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )
    p1_s1, e_p1_s1 = submission_and_evaluation(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant1,
    )
    # participant12, submission 1 to each challenge
    p12_s1_c1, e_p12_s1_c1 = submission_and_evaluation(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.participant12,
    )
    p12_s1_c2, e_p12_s1_c2 = submission_and_evaluation(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        creator=two_challenge_sets.participant12,
    )
    return SubmissionsAndEvaluations(
        p_s1,
        p_s2,
        p1_s1,
        p12_s1_c1,
        p12_s1_c2,
        e_p_s1,
        e_p_s2,
        e_p1_s1,
        e_p12_s1_c1,
        e_p12_s1_c2,
    )


@pytest.mark.django_db
def test_method_list(client, two_challenge_sets):
    validate_admin_only_view(
        viewname="evaluation:method-list",
        two_challenge_set=two_challenge_sets,
        client=client,
    )


@pytest.mark.django_db
def test_method_create(client, two_challenge_sets):
    validate_admin_only_view(
        viewname="evaluation:method-create",
        two_challenge_set=two_challenge_sets,
        client=client,
    )


@pytest.mark.django_db
def test_method_detail(client, two_challenge_sets):
    method = MethodFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.admin,
    )
    validate_admin_only_view(
        viewname="evaluation:method-detail",
        two_challenge_set=two_challenge_sets,
        reverse_kwargs={"pk": method.pk},
        client=client,
    )


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_submission_list(client, two_challenge_sets):
    validate_admin_or_participant_view(
        viewname="evaluation:submission-list",
        two_challenge_set=two_challenge_sets,
        client=client,
    )
    p_s1, p_s2, p1_s1, p12_s1_c1, p12_s1_c2, *_ = submissions_and_evaluations(
        two_challenge_sets
    )
    # Participants should only be able to see their own submissions
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.participant,
    )
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content
    assert str(p12_s1_c1.pk) not in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    # Admins should be able to see all submissions
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert str(p_s1.pk) in response.rendered_content
    assert str(p_s2.pk) in response.rendered_content
    assert str(p1_s1.pk) in response.rendered_content
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    # Only submissions relevant to this challenge should be listed
    response = get_view_for_user(
        viewname="evaluation:submission-list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.participant12,
    )
    assert str(p12_s1_c1.pk) in response.rendered_content
    assert str(p12_s1_c2.pk) not in response.rendered_content
    assert str(p_s1.pk) not in response.rendered_content
    assert str(p_s2.pk) not in response.rendered_content
    assert str(p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_submission_create(client, two_challenge_sets):
    validate_admin_or_participant_view(
        viewname="evaluation:submission-create",
        two_challenge_set=two_challenge_sets,
        client=client,
    )

    response = get_view_for_user(
        viewname="evaluation:submission-create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.participant,
        client=client,
    )

    assert response.status_code == 200
    assert "Creator" not in response.rendered_content


@pytest.mark.django_db
def test_legacy_submission_create(client, two_challenge_sets):
    validate_admin_only_view(
        viewname="evaluation:submission-create-legacy",
        two_challenge_set=two_challenge_sets,
        client=client,
    )

    response = get_view_for_user(
        viewname="evaluation:submission-create-legacy",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        client=client,
    )

    assert response.status_code == 200
    assert "Creator" in response.rendered_content


@pytest.mark.django_db
def test_submission_time_limit(client, two_challenge_sets):
    SubmissionFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )

    def get_submission_view():
        return get_view_for_user(
            viewname="evaluation:submission-create",
            challenge=two_challenge_sets.challenge_set_1.challenge,
            client=client,
            user=two_challenge_sets.challenge_set_1.participant,
        )

    assert "make 9 more" in get_submission_view().rendered_content
    s = SubmissionFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )
    s.created = timezone.now() - timedelta(hours=23)
    s.save()
    assert "make 8 more" in get_submission_view().rendered_content
    s = SubmissionFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )
    s.created = timezone.now() - timedelta(hours=25)
    s.save()
    assert "make 8 more" in get_submission_view().rendered_content


@pytest.mark.django_db
def test_submission_detail(client, two_challenge_sets):
    submission = SubmissionFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        creator=two_challenge_sets.challenge_set_1.participant,
    )
    validate_admin_only_view(
        viewname="evaluation:submission-detail",
        two_challenge_set=two_challenge_sets,
        reverse_kwargs={"pk": submission.pk},
        client=client,
    )


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_evaluation_list(client, two_challenge_sets):
    validate_admin_or_participant_view(
        viewname="evaluation:list",
        two_challenge_set=two_challenge_sets,
        client=client,
    )
    (
        *_,
        e_p_s1,
        e_p_s2,
        e_p1_s1,
        e_p12_s1_c1,
        e_p12_s1_c2,
    ) = submissions_and_evaluations(two_challenge_sets)
    # Participants should only be able to see their own evaluations
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.participant,
    )
    assert str(e_p_s1.pk) in response.rendered_content
    assert str(e_p_s2.pk) in response.rendered_content
    assert str(e_p1_s1.pk) not in response.rendered_content
    assert str(e_p12_s1_c1.pk) not in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content
    # Admins should be able to see all evaluations
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.challenge_set_1.admin,
    )
    assert str(e_p_s1.pk) in response.rendered_content
    assert str(e_p_s2.pk) in response.rendered_content
    assert str(e_p1_s1.pk) in response.rendered_content
    assert str(e_p12_s1_c1.pk) in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content
    # Only evaluations relevant to this challenge should be listed
    response = get_view_for_user(
        viewname="evaluation:list",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        user=two_challenge_sets.participant12,
    )
    assert str(e_p12_s1_c1.pk) in response.rendered_content
    assert str(e_p12_s1_c2.pk) not in response.rendered_content
    assert str(e_p_s1.pk) not in response.rendered_content
    assert str(e_p_s2.pk) not in response.rendered_content
    assert str(e_p1_s1.pk) not in response.rendered_content


@pytest.mark.django_db
def test_leaderboard(client, eval_challenge_set):
    validate_open_view(
        viewname="evaluation:leaderboard",
        challenge_set=eval_challenge_set.challenge_set,
        client=client,
    )


# TODO: test that private results cannot be seen
@pytest.mark.django_db
def test_evaluation_detail(client, eval_challenge_set):
    submission = SubmissionFactory(
        challenge=eval_challenge_set.challenge_set.challenge,
        creator=eval_challenge_set.challenge_set.participant,
    )
    e = EvaluationFactory(submission=submission)
    validate_open_view(
        viewname="evaluation:detail",
        challenge_set=eval_challenge_set.challenge_set,
        reverse_kwargs={"pk": e.pk},
        client=client,
    )
