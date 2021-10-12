import pytest
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from guardian.shortcuts import assign_perm

from tests.factories import UserFactory
from tests.flatpages_tests.factories import FlatPageFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_flatpage_create(client):
    u = UserFactory()
    site = Site.objects.get_current()

    title = "test flatpage"
    content = "some content"
    url = "/test/"

    response = get_view_for_user(
        viewname="flatpages:create",
        client=client,
        method=client.post,
        data={
            "title": title,
            "content": content,
            "url": url,
            "sites": [site.pk],
        },
        user=u,
    )

    assert response.status_code == 403

    assign_perm("flatpages.add_flatpage", u)

    response = get_view_for_user(
        viewname="flatpages:create",
        client=client,
        method=client.post,
        data={
            "title": title,
            "content": content,
            "url": url,
            "sites": [site.pk],
        },
        user=u,
    )

    assert response.status_code == 302
    assert FlatPage.objects.count() == 1
    assert FlatPage.objects.get().url == url


@pytest.mark.django_db
def test_flatpage_update(client):
    u = UserFactory()
    f = FlatPageFactory(
        url="/test-flatpage/", content="some content", title="test flatpage"
    )
    site = Site.objects.get_current()
    f.sites.set([site])

    new_content = "updated content"
    new_title = "new title"

    response = get_view_for_user(
        viewname="flatpages:update",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": f.pk},
        data={"title": new_title, "content": new_content},
        user=u,
    )

    assert response.status_code == 403

    assign_perm("flatpages.change_flatpage", u)

    response = get_view_for_user(
        viewname="flatpages:update",
        client=client,
        method=client.post,
        reverse_kwargs={"pk": f.pk},
        data={"title": new_title, "content": new_content},
        user=u,
    )

    assert response.status_code == 302
    f.refresh_from_db()
    assert f.content == new_content
    assert f.title == new_title
