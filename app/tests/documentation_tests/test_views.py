import pytest
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
def test_docpage_create_title(client):
    u1 = UserFactory()
    p = DocPageFactory()
    assign_perm("documentation.add_docpage", u1)

    title = "overview"

    response = get_view_for_user(
        viewname="documentation:create",
        client=client,
        method=client.post,
        data={"title": title},
        user=u1,
    )

    assert response.status_code == 200
    assert "Overview is not allowed as page title" in response.rendered_content

    title = p.title
    response = get_view_for_user(
        viewname="documentation:create",
        client=client,
        method=client.post,
        data={"title": title},
        user=u1,
    )
    assert response.status_code == 200
    assert "A page with that title already exists" in response.rendered_content
