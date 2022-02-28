import datetime

import pytest
from django.contrib.auth.models import Group
from django.core import mail

from config import settings
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.challenges.tasks import update_challenge_results_cache
from grandchallenge.verifications.models import Verification
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


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
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:request",
        data={
            "title": "Test request",
            "challenge_short_name": "example1234",
            "challenge_type": ChallengeRequest.ChallengeTypeChoices.T2,
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today(),
            "expected_number_of_participants": 10,
            "abstract": "test",
            "contact_email": "test@test.com",
            "organizers": "test",
            "challenge_setup": "test",
            "data_set": "test",
            "submission_assessment": "test",
            "challenge_publication": "test",
            "code_availability": "test",
            "expected_number_of_teams": 10,
            "inference_time_limit": 10,
            "average_size_of_test_image": 10,
            "phase_1_number_of_submissions_per_team": 10,
            "phase_2_number_of_submissions_per_team": 1,
            "phase_1_number_of_test_images": 100,
            "phase_2_number_of_test_images": 200,
            "number_of_tasks": 1,
        },
        user=user,
    )
    assert response.status_code == 302
    assert ChallengeRequest.objects.count() == 1
    assert len(mail.outbox) == 2
    receivers = [address for i in mail.outbox for address in i.to]
    # email to requester and to reviewer
    assert user.email in receivers
    assert reviewer.email in receivers

    request = ChallengeRequest.objects.get()
    # reject request
    request.status = False
    request.save()
    assert len(mail.outbox) == 3
    # rejection email to requester
    assert mail.outbox[2].to == [user.email]
    assert (
        "We are very sorry to have to inform you that we will not be able to host your challenge on our platform"
        in mail.outbox[2].body
    )

    # accept request
    request.status = True
    request.save()
    assert len(mail.outbox) == 4
    # acceptance email to requester
    assert mail.outbox[3].to == [user.email]
    assert (
        "We are happy to inform you that your challenge request has been accepted"
        in mail.outbox[3].body
    )
