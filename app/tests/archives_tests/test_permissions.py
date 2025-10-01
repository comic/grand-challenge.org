import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms, get_users_with_perms

from grandchallenge.archives.models import Archive
from grandchallenge.components.models import InterfaceKindChoices
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestArchivePermissions:
    @pytest.mark.parametrize("public", (True, False))
    def test_archive_permissions(self, public):
        a: Archive = ArchiveFactory(public=public)

        expected_perms = {
            a.editors_group: {
                "view_archive",
                "use_archive",
                "upload_archive",
                "change_archive",
            },
            a.uploaders_group: {
                "view_archive",
                "use_archive",
                "upload_archive",
            },
            a.users_group: {"view_archive", "use_archive"},
        }

        if public:
            reg_and_anon = Group.objects.get(
                name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
            )
            expected_perms[reg_and_anon] = {"view_archive"}

        assert get_groups_with_set_perms(a) == expected_perms
        assert get_users_with_perms(a, with_group_users=False).count() == 0

    @pytest.mark.django_db
    def test_visible_to_public_group_permissions(self):
        g_reg_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )
        a = ArchiveFactory()

        assert "view_archive" not in get_perms(g_reg_anon, a)

        a.public = True
        a.save()

        assert "view_archive" in get_perms(g_reg_anon, a)

        a.public = False
        a.save()

        assert "view_archive" not in get_perms(g_reg_anon, a)


@pytest.mark.parametrize(
    "add_to_group,status",
    [
        (Archive.add_user, 403),
        (Archive.add_uploader, 200),
        (Archive.add_editor, 200),
        (None, 404),
    ],
)
@pytest.mark.django_db
def test_api_archive_item_update_permissions(
    client, settings, add_to_group, status, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    archive = ArchiveFactory()
    user = UserFactory()
    item = ArchiveItemFactory(archive=archive)

    if add_to_group:
        add_to_group(archive, user)

    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.BOOL)

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:archives-item-detail",
            reverse_kwargs={"pk": item.pk},
            data={"values": [{"interface": ci.slug, "value": True}]},
            user=user,
            client=client,
            method=client.patch,
            content_type="application/json",
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == status
