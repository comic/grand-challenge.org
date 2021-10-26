import pytest
from django.core.exceptions import MultipleObjectsReturned
from guardian.shortcuts import assign_perm

from grandchallenge.documentation.models import DocPage
from tests.documentation_tests.factories import DocPageFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view, perm",
    [
        ("documentation:create", "documentation.add_docpage"),
        ("documentation:update", "documentation.change_docpage"),
    ],
)
def test_permissions(client, view, perm):
    u1 = UserFactory()
    p1 = DocPageFactory()

    if view == "documentation:update":
        reverse_kwargs = {"slug": p1.slug}
    else:
        reverse_kwargs = None

    response = get_view_for_user(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs, user=u1,
    )
    assert response.status_code == 403

    # give user permission
    assign_perm(perm, u1)

    response = get_view_for_user(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs, user=u1,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_docpage_create(client):
    u1 = UserFactory()
    assign_perm("documentation.add_docpage", u1)

    content = "<h1>Example content</h1>"
    title = "Test title"

    response = get_view_for_user(
        viewname="documentation:create",
        client=client,
        method=client.post,
        data={"title": title, "content": content},
        user=u1,
    )

    assert response.status_code == 302
    assert DocPage.objects.count() == 1

    response = get_view_for_user(url=response.url, client=client)

    assert response.status_code == 200
    assert content in str(response.content)


@pytest.mark.django_db
def test_docpage_update(client):
    u1 = UserFactory()
    _ = DocPageFactory()
    p2 = DocPageFactory()
    assign_perm("documentation.change_docpage", u1)

    assert p2.order == 2

    new_content = "<h1>New content</h1>"

    # change content and order of p2
    response = get_view_for_user(
        viewname="documentation:update",
        client=client,
        method=client.post,
        reverse_kwargs={"slug": p2.slug},
        data={"title": p2.title, "content": new_content, "position": 1},
        user=u1,
    )

    assert response.status_code == 302
    p2.refresh_from_db()
    assert p2.order == 1
    assert p2.content == new_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, target_pages",
    [
        ("algorithm", [0]),
        ("algoritm", [0]),
        ("alg", [0]),
        ("study", [1]),
        ("content", [0, 1]),
    ],
)
def test_search(client, query, target_pages):
    u1 = UserFactory()
    p1 = DocPageFactory(
        title="algorithms", content="some content about algorithms"
    )
    p2 = DocPageFactory(
        title="reader studies", content="some content about reader studies"
    )
    pages = [p1, p2]

    matching_pages = []
    if len(target_pages) > 1:
        for _ in target_pages:
            matching_pages.append(pages.pop(0))
    else:
        matching_pages = pages.pop(target_pages[0])

    non_matching_pages = pages

    assign_perm("documentation.change_docpage", u1)

    response = get_view_for_user(
        viewname="documentation:home",
        client=client,
        data={"query": query},
        user=u1,
    )

    try:
        assert response.context_data["search_results"].get() == matching_pages
    except MultipleObjectsReturned:
        for match in response.context_data["search_results"].all():
            assert match in matching_pages

    if non_matching_pages:
        assert (
            response.context_data["search_results"].get()
            not in non_matching_pages
        )
