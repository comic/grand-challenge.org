import pytest
from django.utils.text import slugify

from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation
from tests.factories import (
    UserFactory,
    WorkstationFactory,
    StagedFileFactory,
    WorkstationImageFactory,
)
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
    assert w.description is None

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


@pytest.mark.django_db
def test_workstationimage_create(client):
    UserFactory()
    u2 = UserFactory(is_staff=True)
    w1 = WorkstationFactory()
    w2 = WorkstationFactory()
    staged_file = StagedFileFactory(file__filename="example.tar.gz")

    assert w1.workstationimage_set.count() == 0
    assert w2.workstationimage_set.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:image-create",
        reverse_kwargs={"slug": w2.slug},
        user=u2,
        data={
            "chunked_upload": staged_file.file_id,
            "initial_path": "",
            "websocket_port": 1337,
            "http_port": 1234,
        },
    )

    assert response.status_code == 302

    w1.refresh_from_db()
    w2.refresh_from_db()

    assert w1.workstationimage_set.count() == 0

    w2_images = w2.workstationimage_set.all()
    assert len(w2_images) == 1
    assert w2_images[0].creator == u2
    assert w2_images[0].websocket_port == 1337
    assert w2_images[0].http_port == 1234
    assert w2_images[0].staged_image_uuid == staged_file.file_id
    assert w2_images[0].initial_path == ""


@pytest.mark.django_db
def test_workstationimage_detail(client):
    user = UserFactory(is_staff=True)
    ws = WorkstationFactory()
    wsi1, wsi2 = (
        WorkstationImageFactory(workstation=ws),
        WorkstationImageFactory(workstation=ws),
    )

    response = get_view_for_user(
        viewname="workstations:image-detail",
        reverse_kwargs={"slug": ws.slug, "pk": wsi1.pk},
        client=client,
        user=user,
    )

    assert response.status_code == 200
    assert str(wsi1.pk) in response.rendered_content
    assert str(wsi2.pk) not in response.rendered_content
