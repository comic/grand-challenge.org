import pytest
from django.contrib.auth.models import Group
from django.core import mail

from config import settings
from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.challenges.tasks import update_challenge_results_cache
from grandchallenge.evaluation.models import Phase
from grandchallenge.verifications.models import Verification
from tests.challenges_tests.factories import (
    generate_type_1_challenge_request,
    generate_type_2_challenge_request,
)
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_challenge_update(
    client, two_challenge_sets, django_assert_num_queries
):
    c1 = two_challenge_sets.challenge_set_1.challenge
    c2 = two_challenge_sets.challenge_set_2.challenge

    _ = EvaluationFactory(
        submission__phase__challenge=c1, method__phase__challenge=c1
    )
    _ = EvaluationFactory(
        submission__phase__challenge=c2, method__phase__challenge=c2
    )

    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()

    # check the # queries stays the same even with more challenges & evaluations

    c3 = ChallengeFactory()
    _ = EvaluationFactory(
        submission__phase__challenge=c3, method__phase__challenge=c3
    )
    with django_assert_num_queries(4) as _:
        update_challenge_results_cache()


@pytest.mark.django_db
def test_challenge_request_email_workflow(client):
    user = UserFactory()
    Verification.objects.create(user=user, is_verified=True)

    reviewer = UserFactory()
    reviewer_group = Group.objects.get(
        name=settings.CHALLENGE_REVIEWERS_GROUP_NAME
    )
    reviewer_group.user_set.add(reviewer)

    assert len(mail.outbox) == 0

    # request challenge
    request = generate_type_2_challenge_request(creator=user)
    assert ChallengeRequest.objects.count() == 1
    assert len(mail.outbox) == 2
    receivers = [address for i in mail.outbox for address in i.to]
    # email to requester and to reviewer
    assert user.email in receivers
    assert reviewer.email in receivers

    # reject request
    mail.outbox.clear()
    request.status = ChallengeRequest.ChallengeRequestStatusChoices.REJECTED
    request.save()
    assert len(mail.outbox) == 1
    # rejection email to requester
    assert mail.outbox[0].to == [user.email]
    assert (
        "We are very sorry to have to inform you that we will not be able to host your challenge on our platform"
        in mail.outbox[0].body
    )

    # accept request
    mail.outbox.clear()
    request.status = ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
    request.save()
    assert len(mail.outbox) == 1
    # acceptance email to requester
    assert mail.outbox[0].to == [user.email]
    assert (
        "We are happy to inform you that your challenge request has been accepted"
        in mail.outbox[0].body
    )


@pytest.mark.django_db
def test_challenge_created_on_request_acceptance(client):
    user = UserFactory()
    Verification.objects.create(user=user, is_verified=True)
    request = generate_type_2_challenge_request(creator=user)
    # accept request
    request.status = ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
    request.save()

    # challenge gets created
    assert Challenge.objects.count() == 1
    challenge = Challenge.objects.get()
    assert challenge.short_name == request.short_name
    # requester is admin of challenge
    assert user in challenge.admins_group.user_set.all()
    # an algorithm submission phase has been created
    assert challenge.phase_set.count() == 1
    assert (
        challenge.phase_set.get().submission_kind
        == Phase.SubmissionKind.ALGORITHM
    )

    request2 = generate_type_1_challenge_request(creator=user)
    # accept request
    request2.status = ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
    request2.save()
    # for a type 1 challenge, a csv submission phase gets created
    assert Challenge.objects.count() == 2
    challenge2 = Challenge.objects.last()
    assert challenge2.short_name == request2.short_name
    assert user in challenge2.admins_group.user_set.all()
    assert challenge2.phase_set.count() == 1
    assert (
        challenge2.phase_set.get().submission_kind == Phase.SubmissionKind.CSV
    )
