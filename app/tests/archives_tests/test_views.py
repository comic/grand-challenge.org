import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.components.models import InterfaceKind
from grandchallenge.subdomains.utils import reverse
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchiveItemFactory,
    ArchivePermissionRequestFactory,
)
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.test_background_tasks import (
    create_raw_upload_image_session,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.uploads_tests.factories import create_upload_from_file
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_permission_required_views(self, client):
        a = ArchiveFactory()
        u = UserFactory()
        p = ArchivePermissionRequestFactory(archive=a)

        for view_name, kwargs, permission, obj, redirect in [
            ("create", {}, "archives.add_archive", None, None),
            (
                "detail",
                {"slug": a.slug},
                "use_archive",
                a,
                reverse(
                    "archives:permission-request-create",
                    kwargs={"slug": a.slug},
                ),
            ),
            ("update", {"slug": a.slug}, "change_archive", a, None,),
            ("editors-update", {"slug": a.slug}, "change_archive", a, None,),
            ("uploaders-update", {"slug": a.slug}, "change_archive", a, None,),
            ("users-update", {"slug": a.slug}, "change_archive", a, None,),
            (
                "permission-request-update",
                {"slug": a.slug, "pk": p.pk},
                "change_archive",
                a,
                None,
            ),
            ("cases-list", {"slug": a.slug}, "use_archive", a, None,),
            ("cases-create", {"slug": a.slug}, "upload_archive", a, None,),
            (
                "cases-reader-study-update",
                {"slug": a.slug},
                "use_archive",
                a,
                None,
            ),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"archives:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            if redirect is not None:
                assert response.status_code == 302
                assert response.url == redirect
            else:
                assert response.status_code == 403

            assign_perm(permission, u, obj)

            response = _get_view()
            assert response.status_code == 200

            remove_perm(permission, u, obj)

    def test_permission_required_list_views(self, client):
        a = ArchiveFactory()
        u = UserFactory()

        for view_name, kwargs, permission, objs in [
            ("list", {}, "view_archive", {a}),
        ]:

            def _get_view():
                return get_view_for_user(
                    client=client,
                    viewname=f"archives:{view_name}",
                    reverse_kwargs=kwargs,
                    user=u,
                )

            response = _get_view()
            assert response.status_code == 200
            assert set() == {*response.context[-1]["object_list"]}

            assign_perm(permission, u, list(objs))

            response = _get_view()
            assert response.status_code == 200
            assert objs == {*response.context[-1]["object_list"]}

            for obj in objs:
                remove_perm(permission, u, obj)


def add_image_to_archive(image, archive):
    interface = ComponentInterfaceFactory()
    civ = ComponentInterfaceValueFactory(interface=interface, image=image)
    item = ArchiveItemFactory(archive=archive)
    item.values.set([civ])


def create_archive_with_user_and_image(patient_id=""):
    a = ArchiveFactory()
    u = UserFactory()
    i = ImageFactory(patient_id=patient_id)
    add_image_to_archive(i, a)
    a.add_user(u)
    return a, u, i


@pytest.mark.django_db
class TestArchiveViewSetPatients:
    @staticmethod
    def get_view(client, user, archive_pk):
        return get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": archive_pk},
            user=user,
        )

    def test_no_access_archive(self, client):
        a, u, i = create_archive_with_user_and_image()
        a.remove_user(u)
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 404

    def test_empty_archive(self, client):
        a, u, i = create_archive_with_user_and_image()
        a.items.all().delete()
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_archive_no_patients(self, client):
        a, u, i = create_archive_with_user_and_image()
        [add_image_to_archive(ImageFactory(), a) for _ in range(3)]
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_archive_some_patients(self, client):
        a, u, i = create_archive_with_user_and_image()
        patients = [f"Patient {i}" for i in range(3)]
        [add_image_to_archive(ImageFactory(patient_id=p), a) for p in patients]
        response = self.get_view(client, u, a.pk)
        assert response.status_code == 200
        assert set(response.data) == set(patients + [""])


@pytest.mark.django_db
class TestArchiveViewSetStudies:
    @staticmethod
    def get_view(client, user, archive_pk, patient_id):
        return get_view_for_user(
            client=client,
            viewname="api:archive-studies",
            user=user,
            reverse_kwargs={"pk": archive_pk},
            data={"patient_id": patient_id},
        )

    def test_no_access_archive(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        a.remove_user(u)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 404

    def test_single_empty_study(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_multiple_empty_studies_distinct(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        for _ in range(3):
            add_image_to_archive(ImageFactory(patient_id=p_id), a)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_study_some_patients(self, client):
        p_id = "patient_id"
        a, u, i = create_archive_with_user_and_image(p_id)
        studies = [f"Study {i}" for i in range(3)]
        for s in studies:
            i = ImageFactory(patient_id=p_id, study_description=s)
            add_image_to_archive(i, a)
        response = self.get_view(client, u, a.pk, p_id)
        assert response.status_code == 200
        assert set(response.data) == set(studies + [""])


@pytest.mark.django_db
def test_api_archive_item_list_is_filtered(client):
    a1, a2 = ArchiveFactory(), ArchiveFactory()
    a1_editor, user = UserFactory(), UserFactory()
    a1.add_editor(a1_editor)
    _, _ = (
        ArchiveItemFactory(archive=a1),
        ArchiveItemFactory(archive=a1),
    )
    i3 = ArchiveItemFactory(archive=a2)

    # user does not see any archive items
    response = get_view_for_user(
        viewname="api:archives-item-list", user=user, client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0

    # editor of archive 1 sees the items from archive 1, but not from archive 2
    response = get_view_for_user(
        viewname="api:archives-item-list", user=a1_editor, client=client,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert i3.id not in (
        response.json()["results"][0]["id"],
        response.json()["results"][1]["id"],
    )


@pytest.mark.django_db
def test_api_archive_item_retrieve_permissions(client):
    archive = ArchiveFactory()
    editor, user = UserFactory(), UserFactory()
    archive.add_editor(editor)
    i1 = ArchiveItemFactory(archive=archive)

    # editor can retrieve archive item
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=editor,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(i1.pk)

    # user cannot retrieve archive item
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 404

    # add user to archive
    archive.add_user(user)
    response = get_view_for_user(
        viewname="api:archives-item-detail",
        reverse_kwargs={"pk": i1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(i1.pk)


@pytest.mark.django_db
def test_api_archive_item_interface_type_update(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)

    session, _ = create_raw_upload_image_session(
        images=["image10x10x10.mha"], user=editor
    )
    session.refresh_from_db()
    im = session.image_set.get()
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.IMAGE
    )
    civ = ComponentInterfaceValueFactory(interface=ci, image=im)
    item.values.add(civ)
    civ.image.update_viewer_groups_permissions()
    assert item.values.count() == 1

    # change interface type from generic medical image to generic overlay
    # for the already uploaded image
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={
                "values": [
                    {"interface": "generic-overlay", "image": im.api_url},
                ]
            },
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(item.pk)
    item.refresh_from_db()
    # check that the old item was removed and a new one was added with the same
    # image but the new interface type
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == "generic-overlay"
    assert new_civ.image == im
    assert new_civ != civ


@pytest.mark.django_db
def test_api_archive_item_add_and_update_value(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)
    ci = ComponentInterfaceFactory(
        kind=InterfaceKind.InterfaceKindChoices.BOOL
    )
    # add civ
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={"values": [{"interface": ci.slug, "value": True}]},
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    civ = item.values.get()
    assert civ.interface.slug == ci.slug
    assert civ.value
    #  update civ
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={"values": [{"interface": ci.slug, "value": False}]},
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == ci.slug
    assert new_civ != civ


@pytest.mark.django_db
def test_api_archive_item_add_and_update_non_image_file(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    editor = UserFactory()
    archive.add_editor(editor)
    item = ArchiveItemFactory(archive=archive)
    assert item.values.count() == 0
    ci = ComponentInterfaceFactory(kind=InterfaceKind.InterfaceKindChoices.PDF)
    upload = create_upload_from_file(
        creator=editor, file_path=RESOURCE_PATH / "test.pdf"
    )
    # add civ
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={
                "values": [
                    {"interface": ci.slug, "user_upload": upload.api_url},
                ]
            },
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    civ = item.values.get()
    assert civ.interface.slug == ci.slug

    # update civ
    upload2 = create_upload_from_file(
        creator=editor, file_path=RESOURCE_PATH / "test.zip"
    )
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={
                "values": [
                    {"interface": ci.slug, "user_upload": upload2.api_url},
                ]
            },
            user=editor,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 200
    assert response.json()["id"] == str(item.pk)
    item.refresh_from_db()
    assert item.values.count() == 1
    new_civ = item.values.get()
    assert new_civ.interface.slug == ci.slug
    assert new_civ != civ
