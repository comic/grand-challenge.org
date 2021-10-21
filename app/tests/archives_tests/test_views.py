import pytest
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.subdomains.utils import reverse
from tests.archives_tests.factories import (
    ArchiveFactory,
    ArchiveItemFactory,
    ArchivePermissionRequestFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
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


@pytest.mark.django_db
class TestArchiveViewSetPatients:
    @staticmethod
    def _create_archive_with_user():
        a = ArchiveFactory()
        u = UserFactory()
        a.add_user(u)
        return a, u

    @staticmethod
    def _add_image_to_archive(image, archive):
        interface = ComponentInterfaceFactory()
        civ = ComponentInterfaceValueFactory(interface=interface, image=image)
        item = ArchiveItemFactory(archive=archive)
        item.values.set([civ])

    def test_no_access_archive(self, client):
        a, u = self._create_archive_with_user()
        a.remove_user(u)
        response = get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": a.pk},
            user=u,
        )
        assert response.status_code == 404

    def test_empty_archive(self, client):
        a, u = self._create_archive_with_user()
        response = get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": a.pk},
            user=u,
        )
        assert response.status_code == 200
        assert len(response.data) == 0

    def test_archive_no_patients(self, client):
        a, u = self._create_archive_with_user()
        for _ in range(3):
            self._add_image_to_archive(ImageFactory(), a)

        response = get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": a.pk},
            user=u,
        )
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0] == ""

    def test_archive_some_patients(self, client):
        a, u = self._create_archive_with_user()
        for _ in range(3):
            self._add_image_to_archive(ImageFactory(), a)
        patients = []
        for i in range(3):
            p_id = f"Patient {i}"
            patients.append(p_id)
            self._add_image_to_archive(ImageFactory(patient_id=p_id), a)

        response = get_view_for_user(
            client=client,
            viewname="api:archive-patients",
            reverse_kwargs={"pk": a.pk},
            user=u,
        )
        assert response.status_code == 200
        assert set(response.data) == set(patients + [""])
