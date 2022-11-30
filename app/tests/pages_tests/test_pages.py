from datetime import timedelta
from itertools import chain

import pytest
from django.conf import settings
from django.db.models import BLANK_CHOICE_DASH
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.evaluation.tasks import get_average_job_duration_for_phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.pages.models import Page
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import ChallengeFactory, PageFactory, UserFactory
from tests.utils import get_view_for_user, validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view", ["pages:list", "pages:create", "pages:delete"]
)
def test_page_admin_permissions(view, client, two_challenge_sets):
    if view == "pages:delete":
        PageFactory(
            challenge=two_challenge_sets.challenge_set_1.challenge,
            display_title="challenge1pagepermtest",
        )
        reverse_kwargs = {"slug": "challenge1pagepermtest"}
    else:
        reverse_kwargs = None
    validate_admin_only_view(
        viewname=view,
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )


@pytest.mark.django_db
def test_page_update_permissions(client, two_challenge_sets):
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="challenge1page1permissiontest",
    )
    validate_admin_only_view(
        viewname="pages:update",
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs={"slug": p1.slug},
    )


@pytest.mark.django_db
def test_page_list_filter(client, two_challenge_sets):
    """Check that only pages related to this challenge are listed."""
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="challenge1page1",
    )
    p2 = PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        display_title="challenge2page1",
    )
    response = get_view_for_user(
        viewname="pages:list",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
    )
    assert p1.display_title in response.rendered_content
    assert p2.display_title not in response.rendered_content
    response = get_view_for_user(
        viewname="pages:list",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
    )
    assert p1.display_title not in response.rendered_content
    assert p2.display_title in response.rendered_content


@pytest.mark.django_db
def test_page_create(client, two_challenge_sets):
    page_html = "<h1>HELLO WORLD</h1>"
    page_title = "testpage1"
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.admin,
        data={
            "display_title": page_title,
            "html": page_html,
            "permission_level": Page.ALL,
        },
    )
    assert response.status_code == 302
    response = get_view_for_user(url=response.url, client=client)
    assert response.status_code == 200
    assert page_html in str(response.content)
    # Check that it was created in the correct challenge
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        reverse_kwargs={"slug": page_title},
    )
    assert response.status_code == 200
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        reverse_kwargs={"slug": page_title},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_page_update(client, two_challenge_sets):
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1updatetest",
        html="oldhtml",
    )
    # page with the same name in another challenge to check selection
    PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        display_title="page1updatetest",
        html="oldhtml",
    )
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
    )
    assert response.status_code == 200
    assert 'value="page1updatetest"' in response.rendered_content
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
        data={
            "display_title": "editedtitle",
            "permission_level": Page.ALL,
            "html": "newhtml",
        },
    )
    assert response.status_code == 302

    # The slug shouldn't change
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": "page1updatetest"},
    )
    assert response.status_code == 200
    assert "newhtml" in str(response.content)

    # check that the other page is unaffected
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": "page1updatetest"},
    )
    assert response.status_code == 200
    assert "oldhtml" in str(response.content)


@pytest.mark.django_db
def test_page_delete(client, two_challenge_sets):
    # Two pages with the same title, make sure the right one is deleted
    c1p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1",
    )
    c2p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        display_title="page1",
    )
    assert Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()
    response = get_view_for_user(
        viewname="pages:delete",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": "page1"},
    )
    assert response.status_code == 302
    assert not Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()
    response = get_view_for_user(
        url=response.url, client=client, user=two_challenge_sets.admin12
    )
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "page_to_move,move_op,expected",
    [
        (2, Page.UP, [1, 3, 2, 4]),
        (1, Page.DOWN, [1, 3, 2, 4]),
        (2, Page.FIRST, [2, 3, 1, 4]),
        (1, Page.LAST, [1, 4, 2, 3]),
        (0, BLANK_CHOICE_DASH[0], [1, 2, 3, 4]),
    ],
)
def test_page_move(
    page_to_move, move_op, expected, client, two_challenge_sets
):
    pages = [*two_challenge_sets.challenge_set_1.challenge.page_set.all()]
    c2_pages = [*two_challenge_sets.challenge_set_2.challenge.page_set.all()]

    for i in range(3):
        pages.append(
            PageFactory(challenge=two_challenge_sets.challenge_set_1.challenge)
        )
        # Same page name in challenge 2, make sure that these are unaffected
        c2_pages.append(
            PageFactory(
                challenge=two_challenge_sets.challenge_set_2.challenge,
                display_title=pages[i + 1].display_title,
            )
        )

    assert [p.order for p in pages] == [1, 2, 3, 4]
    assert [p.order for p in c2_pages] == [1, 2, 3, 4]

    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": pages[page_to_move].slug},
        data={
            "display_title": pages[page_to_move].display_title,
            "permission_level": pages[page_to_move].permission_level,
            "html": pages[page_to_move].html,
            "move": move_op,
        },
    )

    for p in chain(pages, c2_pages):
        p.refresh_from_db()

    assert response.status_code == 302
    assert [p.order for p in pages] == expected
    assert [p.order for p in c2_pages] == [1, 2, 3, 4]


@pytest.mark.django_db
def test_create_page_with_same_title(client, two_challenge_sets):
    PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1",
    )

    # Creating a page with the same title should be created with a different slug
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.admin,
        data={
            "display_title": "page1",
            "html": "hello",
            "permission_level": Page.ALL,
        },
    )
    assert response.status_code == 302

    challenge_pages = Page.objects.filter(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1",
    )
    assert len(challenge_pages) == 2
    assert challenge_pages[0].slug == "page1"
    assert challenge_pages[1].slug == "page1-2"

    # Creating one in another challenge should work
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.challenge_set_2.admin,
        data={
            "display_title": "page1",
            "html": "hello",
            "permission_level": Page.ALL,
        },
    )
    assert response.status_code == 302
    assert (
        Page.objects.get(
            challenge=two_challenge_sets.challenge_set_2.challenge,
            display_title="page1",
        ).slug
        == "page1"
    )


@pytest.mark.django_db
def test_challenge_statistics_page_permissions(
    client, authenticated_staff_user
):
    challenge = ChallengeFactory()
    admin, reviewer, user = UserFactory.create_batch(3)
    challenge.add_admin(admin)
    assign_perm("challenges.view_challengerequest", reviewer)

    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=user,
        challenge=challenge,
    )
    response.status_code = 404

    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=admin,
        challenge=challenge,
    )
    response.status_code = 404

    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=authenticated_staff_user,
        challenge=challenge,
    )
    response.status_code = 200

    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=reviewer,
        challenge=challenge,
    )
    response.status_code = 200


@pytest.mark.django_db
def test_average_job_duration_calculation():
    challenge = ChallengeFactory()
    phase1, phase2 = PhaseFactory.create_batch(
        2, challenge=challenge, submission_kind=SubmissionKindChoices.ALGORITHM
    )

    ai = AlgorithmImageFactory()

    j1 = AlgorithmJobFactory(
        algorithm_image=ai,
        started_at=now() - timedelta(days=2),
        completed_at=now(),
    )
    _ = AlgorithmJobFactory(
        algorithm_image=ai,
        started_at=now() - timedelta(minutes=2),
        completed_at=now(),
    )
    j1.outputs.add(
        ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(slug="metrics-json-file"),
            value=True,
        )
    )
    e1 = EvaluationFactory(submission__phase=phase1)
    e1.inputs.add(j1.outputs.first())

    duration = get_average_job_duration_for_phase(phase=phase1)

    assert (
        round(duration["average_duration"].total_seconds(), ndigits=2)
        == timedelta(days=2).total_seconds()
    )
    assert (
        round(duration["total_duration"].total_seconds(), ndigits=2)
        == timedelta(days=2).total_seconds()
    )
    assert duration["monthly_spendings"][now().year][
        now().strftime("%B")
    ] == round(
        duration["total_duration"].total_seconds()
        * settings.CHALLENGES_COMPUTE_COST_CENTS_PER_HOUR
        / 3600
        / 100,
        ndigits=2,
    )
    assert (
        len(
            duration["algorithms_submitted_per_month"][now().year][
                now().strftime("%B")
            ]
        )
        == 1
    )
    assert duration["algorithms_submitted_per_month"][now().year][
        now().strftime("%B")
    ] == [str(ai.algorithm.pk)]
