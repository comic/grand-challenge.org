from itertools import chain

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import BLANK_CHOICE_DASH

from grandchallenge.pages.models import Page
from tests.evaluation_tests.factories import PhaseFactory
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
    assert p1.display_title in str(response.content)
    assert p2.display_title not in str(response.content)
    response = get_view_for_user(
        viewname="pages:list",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
    )
    assert p1.display_title not in str(response.content)
    assert p2.display_title in str(response.content)


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
    assert 'value="page1updatetest"' in str(response.content)
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
def test_challenge_statistics_page_permissions(client):
    challenge = ChallengeFactory()
    user = UserFactory()

    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=user,
        challenge=challenge,
    )
    assert response.status_code == 200
    assert "Challenge Costs" not in response.rendered_content

    reviewers = Group.objects.get(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    )
    reviewers.user_set.add(user)
    response = get_view_for_user(
        viewname="pages:statistics",
        client=client,
        user=user,
        challenge=challenge,
    )
    assert response.status_code == 200
    assert "Challenge Costs" in response.rendered_content


@pytest.mark.django_db
def test_should_show_verification_warning():
    challenge = ChallengeFactory()
    PhaseFactory(
        challenge=challenge,
        creator_must_be_verified=False,
    )
    phase = PhaseFactory(
        challenge=challenge,
        creator_must_be_verified=True,
        submissions_limit_per_user_per_period=1,
    )

    assert challenge.should_show_verification_warning is True

    phase.creator_must_be_verified = False
    phase.save()

    del challenge.should_show_verification_warning
    del challenge.visible_phases

    assert challenge.should_show_verification_warning is False


@pytest.mark.django_db
def test_page_markdown_permissions(client):
    page = PageFactory()
    user = UserFactory(is_staff=True)

    def get():
        return get_view_for_user(
            client=client,
            viewname="pages:detail-pandoc",
            reverse_kwargs={
                "challenge_short_name": page.challenge.short_name,
                "slug": page.slug,
                "format": "markdown",
            },
            user=user,
        )

    assert get().status_code == 200

    user.is_staff = False
    user.save()

    assert get().status_code == 403
