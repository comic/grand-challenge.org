import pytest
from django.utils.text import slugify

from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation
from tests.factories import UserFactory, WorkstationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_workstation_create_detail(client):
    user = UserFactory(is_staff=True)

    title = "my Workstation"
    description = "my AWESOME workstation"

    response = get_view_for_user(
        client=client, viewname="workstations:create", user=user
    )
    assert response.status_code == 200

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:create",
        user=user,
        data={"title": title, "description": description},
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "workstations:detail", kwargs={"slug": slugify(title)}
    )

    w = Workstation.objects.get(title=title)
    assert w.title == title
    assert w.description == description

    response = get_view_for_user(url=response.url, client=client, user=user)
    assert title in response.rendered_content
    assert description in response.rendered_content


@pytest.mark.django_db
def test_workstation_list_view(client):
    w1, w2 = WorkstationFactory(), WorkstationFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="workstations:list", client=client, user=user
    )

    assert w1.get_absolute_url() in response.rendered_content
    assert w2.get_absolute_url() in response.rendered_content

    w1.delete()

    response = get_view_for_user(
        viewname="workstations:list", client=client, user=user
    )

    assert w1.get_absolute_url() not in response.rendered_content
    assert w2.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
def test_workstation_update_view(client):
    w = WorkstationFactory()
    user = UserFactory(is_staff=True)
    title = "my Workstation"
    description = "my AWESOME workstation"

    assert w.title != title
    assert w.description == None

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:update",
        reverse_kwargs={"slug": w.slug},
        user=user,
        data={"title": title, "description": description},
    )

    w.refresh_from_db()

    assert response.status_code == 302
    assert w.title == title
    assert w.description == description
