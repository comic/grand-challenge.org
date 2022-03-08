import datetime
from datetime import timedelta

import pytest
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from config import settings
from grandchallenge.challenges.forms import ChallengeRequestForm
from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.challenges_tests.factories import generate_type_2_challenge_request
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_external_challenge_buttons(client):
    create_url = reverse("challenges:external-create")
    list_url = reverse("challenges:external-list")

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list"
    )

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    user = UserFactory()

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list", user=user
    )

    assert create_url not in response.rendered_content
    assert list_url not in response.rendered_content

    assign_perm("challenges.change_externalchallenge", user)

    response = get_view_for_user(
        client=client, viewname="challenges:combined-list", user=user
    )

    assert create_url in response.rendered_content
    assert list_url in response.rendered_content


@pytest.mark.django_db
def test_challenge_list(client):
    c = ChallengeFactory(hidden=False)
    hidden = ChallengeFactory(hidden=True)

    response = get_view_for_user(client=client, viewname="challenges:list")

    assert c.short_name in response.rendered_content
    assert hidden.short_name not in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "phase1_submission_limit,phase1_submissions_open,phase1_submissions_close,phase2_submission_limit,phase2_submissions_open,phase2_submissions_close,expected_status,phase_in_status",
    [
        # both phases are closed (because submission limit 0)
        (
            0,
            None,
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Not accepting submissions',
            None,
        ),
        # both phases closed and completed
        (
            10,
            None,
            now() - timedelta(days=5),
            10,
            None,
            now() - timedelta(days=6),
            '<i class="far fa-clock fa-fw"></i> Challenge completed',
            None,
        ),
        # both phases closed, starting some time in the future
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            now() + timedelta(days=3),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            1,
        ),
        (
            10,
            now() + timedelta(days=3),
            None,
            10,
            now() + timedelta(days=5),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            now() + timedelta(days=5),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        # both phases closed, one completed, one not started yet
        (
            10,
            now() + timedelta(days=5),
            None,
            10,
            None,
            now() - timedelta(days=6),
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            0,
        ),
        (
            10,
            None,
            now() - timedelta(days=5),
            10,
            now() + timedelta(days=6),
            None,
            '<i class="far fa-clock fa-fw"></i> Opening submissions',
            1,
        ),
        # phase 1 open, phase 2 closed
        (
            10,
            None,
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            now() - timedelta(days=1),
            None,
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            now() + timedelta(days=1),
            0,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            now() - timedelta(days=10),
            now() - timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            None,
            now() - timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        (
            10,
            None,
            None,
            10,
            now() + timedelta(days=10),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            0,
        ),
        # phase 1 closed, phase 2 open
        (
            0,
            None,
            None,
            10,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            None,
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            now() - timedelta(days=1),
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        (
            0,
            None,
            None,
            10,
            None,
            now() + timedelta(days=1),
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            1,
        ),
        # both phases open
        (
            10,
            None,
            None,
            10,
            None,
            None,
            '<i class="far fa-clock fa-fw"></i> Accepting submissions',
            None,
        ),
    ],
)
def test_challenge_card_status(
    client,
    phase1_submission_limit,
    phase1_submissions_open,
    phase1_submissions_close,
    phase2_submission_limit,
    phase2_submissions_open,
    phase2_submissions_close,
    expected_status,
    phase_in_status,
):
    ch = ChallengeFactory(hidden=False)
    phase1 = ch.phase_set.first()
    phase2 = PhaseFactory(challenge=ch)
    u = UserFactory()

    phase1.submission_limit = phase1_submission_limit
    phase1.submissions_open_at = phase1_submissions_open
    phase1.submissions_close_at = phase1_submissions_close
    phase2.submission_limit = phase2_submission_limit
    phase2.submissions_open_at = phase2_submissions_open
    phase2.submissions_close_at = phase2_submissions_close
    phase1.save()
    phase2.save()

    response = get_view_for_user(
        client=client, viewname="challenges:list", user=u
    )
    if phase_in_status:
        title = ch.phase_set.order_by("created").all()[phase_in_status].title
        assert f"{expected_status} for {title}" in response.rendered_content
    else:
        assert expected_status in response.rendered_content


@pytest.mark.django_db
def test_challenge_request_type_2_budget_fields_required(client):
    user = UserFactory()
    Verification.objects.create(user=user, is_verified=True)
    # fill all fields except for budget fields
    # for type 1 this form is valid
    data = {
        "creator": user,
        "title": "Test request",
        "challenge_short_name": "example1234",
        "challenge_type": ChallengeRequest.ChallengeTypeChoices.T1,
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + timedelta(days=1),
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
        "number_of_tasks": 1,
    }
    form = ChallengeRequestForm(data=data, creator=user)
    assert form.is_valid()

    # for type 2, the budget fields need to be filled
    data2 = {
        "creator": user,
        "title": "Test request",
        "challenge_short_name": "example1234",
        "challenge_type": ChallengeRequest.ChallengeTypeChoices.T2,
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + timedelta(days=1),
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
        "number_of_tasks": 1,
    }
    form2 = ChallengeRequestForm(data=data2, creator=user)
    assert not form2.is_valid()
    assert "For a type 2 challenge, you need to provide" in str(form2.errors)


@pytest.mark.django_db
def test_challenge_request_budget_calculation(client):
    user = UserFactory()
    Verification.objects.create(user=user, is_verified=True)
    request = generate_type_2_challenge_request(creator=user)
    assert request.budget["Data storage cost for phase 1"] == round(
        request.phase_1_number_of_test_images
        * request.average_size_of_test_image
        * settings.AWS_FILE_STORAGE_COSTS,
        ndigits=2,
    )
    assert request.budget["Compute costs for phase 1"] == round(
        request.phase_1_number_of_submissions_per_team
        * request.expected_number_of_teams
        * request.phase_1_number_of_test_images
        * request.inference_time_limit
        * settings.AWS_COMPUTE_COSTS
        / 60,
        ndigits=2,
    )
    assert request.budget["Compute costs for phase 2"] == round(
        request.phase_2_number_of_submissions_per_team
        * request.expected_number_of_teams
        * request.phase_2_number_of_test_images
        * request.inference_time_limit
        * settings.AWS_COMPUTE_COSTS
        / 60,
        ndigits=2,
    )
    assert request.budget["Data storage cost for phase 2"] == round(
        request.phase_2_number_of_test_images
        * request.average_size_of_test_image
        * settings.AWS_FILE_STORAGE_COSTS,
        ndigits=2,
    )
    assert (
        request.budget["Total phase 2"]
        == request.budget["Data storage cost for phase 2"]
        + request.budget["Compute costs for phase 2"]
    )
    assert request.budget["Docker storage cost"] == round(
        request.average_algorithm_container_size
        * request.average_number_of_containers_per_team
        * request.expected_number_of_teams
        * settings.AWS_DOCKER_STORAGE_COSTS,
        ndigits=2,
    )
    assert (
        request.budget["Total phase 1"]
        == request.budget["Data storage cost for phase 1"]
        + request.budget["Compute costs for phase 1"]
    )
    assert (
        request.budget["Total"]
        == request.budget["Total phase 1"]
        + request.budget["Total phase 2"]
        + request.budget["Docker storage cost"]
    )
