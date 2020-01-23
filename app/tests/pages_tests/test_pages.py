import pytest
from django.db.models import BLANK_CHOICE_DASH

from grandchallenge.pages.models import Page
from tests.factories import PageFactory
from tests.utils import get_view_for_user, validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view", ["pages:list", "pages:create", "pages:delete"]
)
def test_page_admin_permissions(view, client, two_challenge_sets):
    if view == "pages:delete":
        PageFactory(
            challenge=two_challenge_sets.challenge_set_1.challenge,
            title="challenge1pagepermtest",
        )
        reverse_kwargs = {"page_title": "challenge1pagepermtest"}
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
        title="challenge1page1permissiontest",
    )
    validate_admin_only_view(
        viewname="pages:update",
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs={"page_title": p1.title},
    )


@pytest.mark.django_db
def test_page_list_filter(client, two_challenge_sets):
    """Check that only pages related to this challenge are listed."""
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        title="challenge1page1",
    )
    p2 = PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        title="challenge2page1",
    )
    response = get_view_for_user(
        viewname="pages:list",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
    )
    assert p1.title in response.rendered_content
    assert p2.title not in response.rendered_content
    response = get_view_for_user(
        viewname="pages:list",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
    )
    assert p1.title not in response.rendered_content
    assert p2.title in response.rendered_content


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
            "title": page_title,
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
        reverse_kwargs={"page_title": page_title},
    )
    assert response.status_code == 200
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        reverse_kwargs={"page_title": page_title},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_page_update(client, two_challenge_sets):
    p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        title="page1updatetest",
        html="oldhtml",
    )
    # page with the same name in another challenge to check selection
    PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge,
        title="page1updatetest",
        html="oldhtml",
    )
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": p1.title},
    )
    assert response.status_code == 200
    assert 'value="page1updatetest"' in response.rendered_content
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": p1.title},
        data={
            "title": "editedtitle",
            "permission_level": Page.ALL,
            "html": "newhtml",
        },
    )
    assert response.status_code == 302
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": "editedtitle"},
    )
    assert response.status_code == 200
    assert "newhtml" in str(response.content)
    # check that the other page is unaffected
    response = get_view_for_user(
        viewname="pages:detail",
        client=client,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": "page1updatetest"},
    )
    assert response.status_code == 200
    assert "oldhtml" in str(response.content)


@pytest.mark.django_db
def test_page_delete(client, two_challenge_sets):
    # Two pages with the same title, make sure the right one is deleted
    c1p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge, title="page1"
    )
    c2p1 = PageFactory(
        challenge=two_challenge_sets.challenge_set_2.challenge, title="page1"
    )
    assert Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()
    response = get_view_for_user(
        viewname="pages:delete",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": "page1"},
    )
    assert response.status_code == 302
    assert not Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()
    response = get_view_for_user(
        url=response.url, client=client, user=two_challenge_sets.admin12
    )
    assert response.status_code == 200


def assert_page_order(pages, expected):
    for page, order in zip(pages, expected):
        assert Page.objects.get(pk=page.pk).order == order


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
    pages = []
    c2_pages = []
    for i in range(4):
        pages.append(
            PageFactory(challenge=two_challenge_sets.challenge_set_1.challenge)
        )
        # Same page name in challenge 2, make sure that these are unaffected
        c2_pages.append(
            PageFactory(
                challenge=two_challenge_sets.challenge_set_2.challenge,
                title=pages[i].title,
            )
        )
    assert_page_order(pages, [1, 2, 3, 4])
    assert_page_order(c2_pages, [1, 2, 3, 4])
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": pages[page_to_move].title},
        data={
            "title": pages[page_to_move].title,
            "permission_level": pages[page_to_move].permission_level,
            "html": pages[page_to_move].html,
            "move": move_op,
        },
    )
    assert response.status_code == 302
    assert_page_order(pages, expected)
    assert_page_order(c2_pages, [1, 2, 3, 4])


@pytest.mark.django_db
def test_create_page_with_same_title(client, two_challenge_sets):
    PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge, title="page1"
    )
    # Creating a page with the same title should be denied
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.challenge_set_1.admin,
        data={"title": "page1", "html": "hello", "permission_level": Page.ALL},
    )
    assert response.status_code == 200
    assert "A page with that title already exists" in response.rendered_content
    # Creating one in another challenge should work
    response = get_view_for_user(
        viewname="pages:create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=two_challenge_sets.challenge_set_2.admin,
        data={"title": "page1", "html": "hello", "permission_level": Page.ALL},
    )
    assert response.status_code == 302
    # Check the updating
    PageFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge, title="page2"
    )
    response = get_view_for_user(
        viewname="pages:update",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=two_challenge_sets.admin12,
        reverse_kwargs={"page_title": "page2"},
        data={
            "title": "page1",
            "html": " ",
            "permission_level": Page.ALL,
            "move": BLANK_CHOICE_DASH[0],
        },
    )
    assert response.status_code == 200
    assert "A page with that title already exists" in response.rendered_content
