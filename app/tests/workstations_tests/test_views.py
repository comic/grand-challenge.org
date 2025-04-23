import json
from urllib.parse import quote_plus

import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.http import Http404
from django.utils.text import slugify
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.reader_studies.models import InteractiveAlgorithmChoices
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Session, Workstation
from grandchallenge.workstations.templatetags.workstations import (
    get_workstation_path_and_query_string,
)
from grandchallenge.workstations.views import SessionCreate
from tests.factories import (
    ImageFactory,
    SessionFactory,
    UserFactory,
    WorkstationFactory,
    WorkstationImageFactory,
)
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    QuestionFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.fixture
def workstation_creator():
    u = UserFactory()
    g = Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)
    g.user_set.add(u)
    return u


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        ws = WorkstationFactory()
        wsi = WorkstationImageFactory(workstation=ws)
        u = UserFactory()
        VerificationFactory(user=u, is_verified=True)

        def _get_view():
            return get_view_for_user(
                client=client,
                viewname=f"workstations:{_view_name}",
                reverse_kwargs={
                    "slug": ws.slug,
                    "pk": wsi.pk,
                    **_kwargs,
                },
                user=u,
            )

        for _view_name, _kwargs, permission, obj in [
            (
                "image-import-status-detail",
                {},
                "view_workstationimage",
                wsi,
            ),
        ]:
            response = _get_view()

            assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()

            assert response.status_code == 200

            remove_perm(permission, u, obj)


@pytest.mark.django_db
def test_workstation_create_detail(
    client, workstation_creator, uploaded_image
):
    user = workstation_creator

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
            "logo": uploaded_image(),
        },
    )
    assert response.status_code == 302
    assert response.url == reverse(
        "workstations:detail", kwargs={"slug": slugify(title)}
    )

    w = Workstation.objects.get(title=title)
    assert w.title == title
    assert w.description == description

    assert w.is_editor(user=user)

    response = get_view_for_user(url=response.url, client=client, user=user)
    assert title in response.rendered_content
    assert description in response.rendered_content


@pytest.mark.django_db
def test_workstation_list_view(client):
    w1, w2 = WorkstationFactory(), WorkstationFactory()
    user = UserFactory()
    response = get_view_for_user(
        viewname="workstations:list", client=client, user=user
    )

    assert w1.get_absolute_url() not in response.rendered_content
    assert w2.get_absolute_url() not in response.rendered_content

    w2.add_editor(user=user)

    response = get_view_for_user(
        viewname="workstations:list", client=client, user=user
    )

    assert w1.get_absolute_url() not in response.rendered_content
    assert w2.get_absolute_url() in response.rendered_content

    w1u = UserFactory()
    w1.add_user(user=w1u)

    response = get_view_for_user(
        viewname="workstations:list", client=client, user=w1u
    )

    assert w1.get_absolute_url() in response.rendered_content
    assert w2.get_absolute_url() not in response.rendered_content


@pytest.mark.django_db
def test_workstation_update_view(client):
    w = WorkstationFactory()
    user = UserFactory()
    w.add_editor(user=user)

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
    u2 = UserFactory()
    VerificationFactory(user=u2, is_verified=True)
    w1 = WorkstationFactory()
    w2 = WorkstationFactory()

    w2.add_editor(user=u2)

    user_upload = UserUploadFactory(filename="test_image.tar.gz", creator=u2)
    user_upload.status = user_upload.StatusChoices.COMPLETED
    user_upload.save()

    assert w1.workstationimage_set.count() == 0
    assert w2.workstationimage_set.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:image-create",
        reverse_kwargs={"slug": w2.slug},
        user=u2,
        data={
            "user_upload": user_upload.pk,
            "creator": u2.pk,
            "workstation": w2.pk,
            "initial_path": "a",
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
    assert w2_images[0].user_upload == user_upload
    assert w2_images[0].initial_path == "a"


@pytest.mark.django_db
def test_workstationimage_detail(client):
    user = UserFactory()
    ws = WorkstationFactory()
    wsi1, wsi2 = (
        WorkstationImageFactory(workstation=ws),
        WorkstationImageFactory(workstation=ws),
    )

    ws.add_editor(user=user)

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
    user = UserFactory()
    wsi = WorkstationImageFactory()

    wsi.workstation.add_editor(user=user)

    assert wsi.initial_path != ""
    assert wsi.websocket_port != 1337
    assert wsi.http_port != 1234

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:image-update",
        reverse_kwargs={"slug": wsi.workstation.slug, "pk": wsi.pk},
        user=user,
        data={"initial_path": "a", "websocket_port": 1337, "http_port": 1234},
    )

    assert response.status_code == 302
    assert response.url == wsi.get_absolute_url()

    wsi.refresh_from_db()

    assert wsi.initial_path == "a"
    assert wsi.websocket_port == 1337
    assert wsi.http_port == 1234


@pytest.mark.django_db
def test_session_create(client):
    user = UserFactory()
    ws = WorkstationFactory()

    ws.add_user(user=user)

    # Create some workstations and pretend that they're ready
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=False,
        is_desired_version=True,
    )  # not in registry
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=False,
        is_in_registry=True,
        is_desired_version=True,
    )  # invalid manifest
    wsi_new_ready = WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    WorkstationImageFactory(workstation=ws)  # WSI not ready
    WorkstationImageFactory(
        is_manifest_valid=True, is_in_registry=True
    )  # Image for some other ws

    assert Session.objects.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:workstation-session-create",
        reverse_kwargs={"slug": ws.slug},
        user=user,
        data={"region": "eu-central-1"},
    )

    assert response.status_code == 302

    sessions = Session.objects.all()

    assert len(sessions) == 1

    # Should select the most recent workstation
    assert sessions[0].workstation_image == wsi_new_ready
    assert sessions[0].extra_env_vars == []
    assert sessions[0].creator == user
    assert response.url == sessions[0].get_absolute_url() + "?path="


@pytest.mark.django_db
def test_session_create_reader_study(
    client, django_capture_on_commit_callbacks
):
    user = UserFactory()
    ws = WorkstationFactory()
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    reader_study = ReaderStudyFactory(workstation=ws)
    QuestionFactory(
        reader_study=reader_study,
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )

    reader_study.readers_group.user_set.add(user)

    path, _ = get_workstation_path_and_query_string(reader_study=reader_study)

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            client=client,
            method=client.post,
            viewname="workstations:workstation-session-create-nested",
            reverse_kwargs={"slug": ws.slug, "workstation_path": path},
            user=user,
            data={"region": "eu-central-1"},
        )

    assert response.status_code == 302
    assert [c.__self__.name for c in callbacks] == [
        "grandchallenge.components.tasks.start_service",
        "grandchallenge.components.tasks.preload_interactive_algorithms",
        "grandchallenge.components.tasks.stop_service",
    ]
    assert reader_study.workstation_sessions.count() == 1


@pytest.mark.django_db
def test_session_create_reader_study_no_algorithm(
    client, django_capture_on_commit_callbacks
):
    user = UserFactory()
    ws = WorkstationFactory()
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    reader_study = ReaderStudyFactory(workstation=ws)
    QuestionFactory(reader_study=reader_study)

    reader_study.readers_group.user_set.add(user)

    path, _ = get_workstation_path_and_query_string(reader_study=reader_study)

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            client=client,
            method=client.post,
            viewname="workstations:workstation-session-create-nested",
            reverse_kwargs={"slug": ws.slug, "workstation_path": path},
            user=user,
            data={"region": "eu-central-1"},
        )

    assert response.status_code == 302
    assert [c.__self__.name for c in callbacks] == [
        "grandchallenge.components.tasks.start_service",
        "grandchallenge.components.tasks.stop_service",
    ]
    assert reader_study.workstation_sessions.count() == 1


@pytest.mark.django_db
def test_session_create_reader_study_not_launchable(
    client, django_capture_on_commit_callbacks
):
    user = UserFactory()
    ws = WorkstationFactory()
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    reader_study = ReaderStudyFactory(workstation=ws, max_credits=0)
    QuestionFactory(reader_study=reader_study)
    reader_study.readers_group.user_set.add(user)
    path, _ = get_workstation_path_and_query_string(reader_study=reader_study)

    assert not reader_study.is_launchable
    assert Session.objects.count() == 0

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            client=client,
            method=client.post,
            viewname="workstations:workstation-session-create-nested",
            reverse_kwargs={"slug": ws.slug, "workstation_path": path},
            user=user,
            data={"region": "eu-central-1"},
        )

    assert response.status_code == 403
    assert [c.__self__.name for c in callbacks] == [
        "grandchallenge.components.tasks.start_service",
        "grandchallenge.components.tasks.stop_service",
    ]
    assert Session.objects.count() == 1
    assert reader_study.workstation_sessions.count() == 0


@pytest.mark.django_db
def test_session_create_display_set(
    client, django_capture_on_commit_callbacks
):
    user = UserFactory()
    ws = WorkstationFactory()
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    reader_study = ReaderStudyFactory(workstation=ws)
    QuestionFactory(
        reader_study=reader_study,
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    display_set = DisplaySetFactory(reader_study=reader_study)

    reader_study.readers_group.user_set.add(user)

    path, _ = get_workstation_path_and_query_string(display_set=display_set)

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            client=client,
            method=client.post,
            viewname="workstations:workstation-session-create-nested",
            reverse_kwargs={"slug": ws.slug, "workstation_path": path},
            user=user,
            data={"region": "eu-central-1"},
        )

    assert response.status_code == 302
    assert [c.__self__.name for c in callbacks] == [
        "grandchallenge.components.tasks.start_service",
        "grandchallenge.components.tasks.preload_interactive_algorithms",
        "grandchallenge.components.tasks.stop_service",
    ]
    assert reader_study.workstation_sessions.count() == 1


@pytest.mark.django_db
def test_session_create_image(client, django_capture_on_commit_callbacks):
    user = UserFactory()
    ws = WorkstationFactory()
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    reader_study = ReaderStudyFactory(workstation=ws)
    image = ImageFactory()

    reader_study.readers_group.user_set.add(user)

    path, _ = get_workstation_path_and_query_string(image=image)

    with django_capture_on_commit_callbacks() as callbacks:
        response = get_view_for_user(
            client=client,
            method=client.post,
            viewname="workstations:workstation-session-create-nested",
            reverse_kwargs={"slug": ws.slug, "workstation_path": path},
            user=user,
            data={"region": "eu-central-1"},
        )

    assert response.status_code == 302
    # No callback to preload_interactive_algorithms should be done for non-reader studies
    assert [c.__self__.name for c in callbacks] == [
        "grandchallenge.components.tasks.start_service",
        "grandchallenge.components.tasks.stop_service",
    ]
    assert reader_study.workstation_sessions.count() == 0


@pytest.mark.django_db
def test_session_create_redirect_url(client):
    user = UserFactory()
    ws = WorkstationFactory()

    ws.add_user(user=user)
    WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    assert Session.objects.count() == 0

    test_path = "path/with/special_characters$?="
    test_qs = "query=string&test"

    response = get_view_for_user(
        client=client,
        method=client.post,
        url=reverse(
            "workstations:workstation-session-create", kwargs={"slug": ws.slug}
        ),
        user=user,
        data={"region": "eu-central-1"},
    )

    assert response.status_code == 302
    sessions = Session.objects.all()
    assert response.url == sessions[0].get_absolute_url() + "?path="

    response = get_view_for_user(
        client=client,
        method=client.post,
        url=reverse(
            "workstations:workstation-session-create-nested",
            kwargs={"slug": ws.slug, "workstation_path": test_path},
        ),
        user=user,
        data={"region": "eu-central-1"},
    )

    assert response.status_code == 302
    assert (
        response.url
        == sessions[0].get_absolute_url() + f"?path={quote_plus(test_path)}"
    )

    response = get_view_for_user(
        client=client,
        method=client.post,
        url=reverse(
            "workstations:workstation-session-create-nested",
            kwargs={"slug": ws.slug, "workstation_path": test_path},
        )
        + "?"
        + test_qs,
        user=user,
        data={"region": "eu-central-1"},
    )

    assert response.status_code == 302
    assert (
        response.url
        == sessions[0].get_absolute_url()
        + f"?path={quote_plus(test_path)}&qs={quote_plus(test_qs)}"
    )


@pytest.mark.django_db
def test_debug_session_create(client):
    user = UserFactory()
    ws = WorkstationFactory()
    env_vars = [{"name": "TEST", "value": "12345"}]

    ws.add_editor(user=user)

    wsi = WorkstationImageFactory(
        workstation=ws,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    assert Session.objects.count() == 0

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:workstation-debug-session-create",
        reverse_kwargs={"slug": ws.slug},
        user=user,
        data={
            "region": "eu-central-1",
            "extra_env_vars": json.dumps(env_vars),
        },
    )

    assert response.status_code == 302

    session = Session.objects.get()

    assert session.workstation_image == wsi
    assert session.creator == user
    assert session.extra_env_vars == env_vars
    assert response.url == session.get_absolute_url() + "?path="


@pytest.mark.django_db
def test_session_redirect(client):
    user = UserFactory()
    default_workstation = Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    wsi = WorkstationImageFactory(
        workstation=default_workstation,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )

    wsi.workstation.add_user(user=user)

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="workstations:default-session-create",
        user=user,
        data={"region": "eu-central-1"},
    )

    assert response.status_code == 302

    response = get_view_for_user(client=client, user=user, url=response.url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_session_detail(client):
    s1, s2 = SessionFactory(), SessionFactory()
    response = get_view_for_user(
        client=client,
        viewname="session-detail",
        reverse_kwargs={
            "slug": s1.workstation_image.workstation.slug,
            "pk": s1.pk,
            "rendering_subdomain": s1.region,
        },
        user=s1.creator,
    )

    assert response.status_code == 200
    assert str(s1.pk) in response.rendered_content
    assert str(s2.pk) not in response.rendered_content


@pytest.mark.django_db
def test_workstation_proxy(client):
    u1, u2 = UserFactory(), UserFactory()
    session = SessionFactory(creator=u1)

    url = reverse(
        "session-proxy",
        kwargs={
            "slug": session.workstation_image.workstation.slug,
            "pk": session.pk,
            "path": "foo/bar/../baz/test",
            "rendering_subdomain": session.region,
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


@pytest.mark.django_db
@pytest.mark.parametrize("new_user", [False, True])
def test_workstation_group_update(client, two_workstation_sets, new_user):
    new_editor = not new_user  # Only tests for editors and users groups
    group = "users" if new_user else "editors"

    u = UserFactory()

    assert not two_workstation_sets.ws1.workstation.is_editor(user=u)
    assert not two_workstation_sets.ws1.workstation.is_user(user=u)
    assert not two_workstation_sets.ws2.workstation.is_editor(user=u)
    assert not two_workstation_sets.ws2.workstation.is_user(user=u)

    response = get_view_for_user(
        client=client,
        viewname=f"workstations:{group}-update",
        method=client.post,
        reverse_kwargs={"slug": two_workstation_sets.ws1.workstation.slug},
        user=two_workstation_sets.ws1.editor,
        data={"action": "ADD", "user": u.pk},
        follow=True,
    )
    assert response.status_code == 200

    assert two_workstation_sets.ws1.workstation.is_editor(user=u) == new_editor
    assert two_workstation_sets.ws1.workstation.is_user(user=u) == new_user
    assert not two_workstation_sets.ws2.workstation.is_editor(user=u)
    assert not two_workstation_sets.ws2.workstation.is_user(user=u)

    response = get_view_for_user(
        client=client,
        viewname=f"workstations:{group}-update",
        method=client.post,
        reverse_kwargs={"slug": two_workstation_sets.ws1.workstation.slug},
        user=two_workstation_sets.ws1.editor,
        data={"action": "REMOVE", "user": u.pk},
        follow=True,
    )
    assert response.status_code == 200

    assert not two_workstation_sets.ws1.workstation.is_editor(user=u)
    assert not two_workstation_sets.ws1.workstation.is_user(user=u)
    assert not two_workstation_sets.ws2.workstation.is_editor(user=u)
    assert not two_workstation_sets.ws2.workstation.is_user(user=u)


@pytest.mark.django_db
def test_workstation_image(rf):
    request = rf.get("/")
    view = SessionCreate()
    view.setup(request)

    with pytest.raises(Http404):
        # No default workstation
        _ = view.workstation_image

    default_workstation = Workstation.objects.get(
        slug=settings.DEFAULT_WORKSTATION_SLUG
    )
    default_wsi = WorkstationImageFactory(
        workstation=default_workstation,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    wsi = WorkstationImageFactory(
        is_manifest_valid=True, is_in_registry=True, is_desired_version=True
    )

    assert view.workstation_image == default_wsi

    view.setup(request, slug=wsi.workstation.slug)
    del view.workstation_image
    assert view.workstation_image == wsi

    # No images for workstation
    view.setup(request, slug=WorkstationFactory().slug)
    del view.workstation_image
    with pytest.raises(Http404):
        _ = view.workstation_image


@pytest.mark.django_db
def test_workstation_image_move(client):
    user = UserFactory()
    old_workstation = WorkstationFactory()
    new_workstation = WorkstationFactory()

    move_image = WorkstationImageFactory(
        workstation=old_workstation,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    _ = WorkstationImageFactory(
        workstation=old_workstation,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=False,
    )
    replace_image = WorkstationImageFactory(
        workstation=old_workstation,
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=False,
    )

    old_workstation.add_editor(user=user)
    new_workstation.add_editor(user=user)

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="workstations:image-move",
        reverse_kwargs={"pk": move_image.pk, "slug": old_workstation.slug},
        data={
            "new_workstation": str(new_workstation.pk),
        },
        method=client.post,
    )

    assert response.status_code == 302

    assert old_workstation.active_image == replace_image
    assert new_workstation.active_image == move_image
