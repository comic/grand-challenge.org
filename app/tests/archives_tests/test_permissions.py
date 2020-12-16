import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_perms, get_users_with_perms

from grandchallenge.archives.models import Archive
from tests.archives_tests.factories import ArchiveFactory
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms


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
