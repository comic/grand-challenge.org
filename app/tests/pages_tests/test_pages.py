from itertools import chain

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import BLANK_CHOICE_DASH
from django.urls import URLPattern, URLResolver

from config.urls import challenge_subdomain
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
        viewname="pages:content-update",
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
    page_markdown = "# HELLO WORLD"
    page_title = "testpage1"
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.admin,
        data={
            "display_title": page_title,
            "permission_level": Page.ALL,
        },
    )
    assert response.status_code == 302
    assert response.url.endswith(f"{page_title}/content-update/")
    response = get_view_for_user(
        url=response.url,
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.admin,
        data={
            "content_markdown": page_markdown,
        },
    )
    assert response.status_code == 302
    response = get_view_for_user(url=response.url, client=client)
    assert response.status_code == 200
    assert (
        '<h1 id="hello-world">HELLO WORLD<a class="headerlink text-muted small pl-1" href="#hello-world" title="Permanent link">¶</a></h1>'
        in response.content.decode("utf-8")
    )
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
def test_page_create_permission(client):
    def attempt_create():
        return get_view_for_user(
            viewname="pages:create",
            client=client,
            method=client.post,
            challenge=challenge,
            data={
                "display_title": "page 1",
                "permission_level": Page.ALL,
            },
            user=user,
        )

    user = UserFactory()
    challenge = ChallengeFactory()
    n_pages = Page.objects.count()
    response = attempt_create()
    assert response.status_code == 403
    assert Page.objects.count() == n_pages

    challenge.add_admin(user=user)

    response = attempt_create()
    assert response.status_code == 302
    assert Page.objects.count() == n_pages + 1
    assert Page.objects.all()[n_pages].display_title == "page 1"


@pytest.mark.django_db
def test_page_metadata_update(client, two_challenge_sets):
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1metadatatest",
        content_markdown="",
    )
    # page with the same name in another challenge to check selection
    PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        display_title="page1metadatatest",
        content_markdown="",
    )
    response = get_view_for_user(
        viewname="pages:metadata-update",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
    )
    assert response.status_code == 200
    assert 'value="page1metadatatest"' in str(response.content)
    response = get_view_for_user(
        viewname="pages:metadata-update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
        data={
            "display_title": "editedtitle",
            "permission_level": Page.ALL,
        },
    )
    assert response.status_code == 302

    # The slug shouldn't change
    response = get_view_for_user(
        viewname="pages:metadata-update",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": "page1metadatatest"},
    )
    assert response.status_code == 200
    assert 'value="editedtitle"' in str(response.content)

    # check that the other page is unaffected
    response = get_view_for_user(
        viewname="pages:metadata-update",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": "page1metadatatest"},
    )
    assert response.status_code == 200
    assert 'value="page1metadatatest"' in str(response.content)


@pytest.mark.django_db
def test_page_metadata_update_permission(client):
    def attempt_metadata_update():
        return get_view_for_user(
            viewname="pages:metadata-update",
            client=client,
            method=client.post,
            challenge=page.challenge,
            data={
                "display_title": "new title",
                "permission_level": Page.ALL,
            },
            reverse_kwargs={"slug": page.slug},
            user=user,
        )

    user = UserFactory()
    page = PageFactory(display_title="old title")

    response = attempt_metadata_update()
    assert response.status_code == 403

    page.challenge.add_admin(user=user)

    response = attempt_metadata_update()
    assert response.status_code == 302

    page.refresh_from_db()
    assert page.display_title == "new title"


@pytest.mark.django_db
def test_page_content_update(client, two_challenge_sets):
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        display_title="page1updatetest",
        content_markdown="oldhtml",
    )
    # page with the same name in another challenge to check selection
    PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        display_title="page1updatetest",
        content_markdown="oldhtml",
    )
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
    )
    assert response.status_code == 200
    assert "oldhtml" in str(response.content)
    response = get_view_for_user(
        viewname="pages:content-update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": p1.slug},
        data={
            "content_markdown": "newhtml",
        },
    )
    assert response.status_code == 302

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
def test_page_content_update_permission(client):
    def attempt_content_update():
        return get_view_for_user(
            viewname="pages:content-update",
            client=client,
            method=client.post,
            challenge=page.challenge,
            data={
                "content_markdown": "new content",
            },
            reverse_kwargs={"slug": page.slug},
            user=user,
        )

    user = UserFactory()
    page = PageFactory(content_markdown="old content")

    response = attempt_content_update()

    assert response.status_code == 403

    page.challenge.add_admin(user=user)

    response = attempt_content_update()
    page.refresh_from_db()

    assert response.status_code == 302
    assert page.content_markdown == "new content"


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
        (0, Page.UP, [1, 2, 3, 4]),
        (3, Page.DOWN, [1, 2, 3, 4]),
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
        viewname="pages:metadata-update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"slug": pages[page_to_move].slug},
        data={
            "display_title": pages[page_to_move].display_title,
            "permission_level": pages[page_to_move].permission_level,
            "content_markdown": pages[page_to_move].content_markdown,
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
def test_challenge_subdomain_patterns():
    def resolve_and_check_patterns(items, base_url=None):
        if base_url is None:
            base_url = ""
        for p in items:
            if isinstance(p, URLResolver):
                resolve_and_check_patterns(
                    p.url_patterns, base_url + str(p.pattern)
                )
            elif isinstance(p, URLPattern):
                url = base_url + str(p.pattern)
                check_url_pattern(url=url, pattern=p)

    def check_url_pattern(url, pattern):
        nonlocal invalid_patterns
        if (
            url.count("/") == 1
            and url.endswith("/")
            and pattern.lookup_str != "grandchallenge.pages.views.PageDetail"
        ):
            # these patterns will clash if challenge admins use it as a page title
            invalid_patterns.append(url)

    invalid_patterns = []
    resolve_and_check_patterns(challenge_subdomain.urlpatterns)

    assert (
        invalid_patterns == []
    ), f"These patterns will clash with page urls if challenge admins create a page with the same slug: {invalid_patterns}"
