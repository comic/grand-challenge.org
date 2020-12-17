import pytest
from guardian.shortcuts import get_users_with_perms

from grandchallenge.organizations.models import Organization
from tests.evaluation_tests.test_permissions import get_groups_with_set_perms
from tests.organizations_tests.factories import OrganizationFactory


@pytest.mark.django_db
class TestOrganizationPermissions:
    def test_organization_permissions(self):
        o: Organization = OrganizationFactory()

        assert get_groups_with_set_perms(o) == {
            o.editors_group: {"change_organization"}
        }
        assert not get_users_with_perms(o, with_group_users=False).exists()
