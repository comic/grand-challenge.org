import pytest

from django.conf import settings
from django.utils.text import slugify

from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation, Session
from tests.factories import (
    UserFactory,
    WorkstationFactory,
    StagedFileFactory,
    WorkstationImageFactory,
    SessionFactory,
)
from tests.utils import get_view_for_user, get_temporary_image


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
        data={
            "title": title,
            "description": description,
            "logo": get_temporary_image(),
        },
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


@pytest.mark.django_db
def test_workstationimage_update(client):
    user = UserFactory(is_staff=True)
    wsi = WorkstationImageFactory()

    assert wsi.initial_path != ""
    assert wsi.websocket_port != 1337
    assert wsi.http_port != 1234

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:image-update",
        reverse_kwargs={"slug": wsi.workstation.slug, "pk": wsi.pk},
        user=user,
        data={"initial_path": "", "websocket_port": 1337, "http_port": 1234},
    )

    assert response.status_code == 302
    assert response.url == wsi.get_absolute_url()

    wsi.refresh_from_db()

    assert wsi.initial_path == ""
    assert wsi.websocket_port == 1337
    assert wsi.http_port == 1234


@pytest.mark.django_db
def test_session_create(client):
    user = UserFactory(is_staff=True)
    ws = WorkstationFactory()

    # Create some workstations and pretend that they're ready
    wsi_old = WorkstationImageFactory(workstation=ws, ready=True)
    wsi_new = WorkstationImageFactory(workstation=ws, ready=True)
    wsi_not_ready = WorkstationImageFactory(workstation=ws)
    wsi_other_ws = WorkstationImageFactory(ready=True)

    assert Session.objects.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:session-create",
        reverse_kwargs={"slug": ws.slug},
        user=user,
    )

    assert response.status_code == 302

    sessions = Session.objects.all()

    assert len(sessions) == 1

    # Should select the most recent workstation
    assert sessions[0].workstation_image == wsi_new
    assert sessions[0].creator == user


@pytest.mark.django_db
def test_session_update(client):
    user = UserFactory(is_staff=True)
    session = SessionFactory()

    assert session.user_finished == False

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:session-update",
        reverse_kwargs={
            "slug": session.workstation_image.workstation.slug,
            "pk": session.pk,
        },
        user=user,
        data={"user_finished": True},
    )

    assert response.status_code == 302
    assert response.url == session.get_absolute_url()

    session.refresh_from_db()

    assert session.user_finished == True


@pytest.mark.django_db
def test_session_redirect(client):
    user = UserFactory(is_staff=True)
    WorkstationImageFactory(
        workstation__title=settings.DEFAULT_WORKSTATION_SLUG, ready=True
    )

    response = get_view_for_user(
        client=client,
        viewname="workstations:default-session-redirect",
        user=user,
    )

    assert response.status_code == 302

    response = get_view_for_user(client=client, user=user, url=response.url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_session_detail(client):
    user = UserFactory(is_staff=True)
    s1, s2 = SessionFactory(), SessionFactory()

    response = get_view_for_user(
        client=client,
        viewname="workstations:session-detail",
        reverse_kwargs={
            "slug": s1.workstation_image.workstation.slug,
            "pk": s1.pk,
        },
        user=user,
    )

    assert response.status_code == 200
    assert str(s1.pk) in response.rendered_content
    assert str(s2.pk) not in response.rendered_content


@pytest.mark.django_db
def test_workstation_proxy(client):
    u1, u2 = UserFactory(), UserFactory()
    session = SessionFactory(creator=u1)

    url = reverse(
        "workstations:session-proxy",
        kwargs={
            "slug": session.workstation_image.workstation.slug,
            "pk": session.pk,
            "path": "foo/bar/../baz/test",
        },
    )

    response = get_view_for_user(client=client, url=url, user=u1)

    assert response.status_code == 200
    assert response.has_header("X-Accel-Redirect")

    redirect_url = response.get("X-Accel-Redirect")

    assert redirect_url.endswith("foo/baz/test")
    assert redirect_url.startswith("/workstation-proxy/")
    assert session.hostname in redirect_url

    # try as another user
    response = get_view_for_user(client=client, url=url, user=u2)
    assert not response.has_header("X-Accel-Redirect")
    assert response.status_code == 403
