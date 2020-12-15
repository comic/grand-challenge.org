import pytest

from tests.organizations_tests.factories import OrganizationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestObjectPermissionRequiredViews:
    def test_open_views(self, client):
        o = OrganizationFactory()

        for viewname, kwargs in (("list", {}), ("detail", {"slug": o.slug})):
            response = get_view_for_user(
                client=client,
                viewname=f"organizations:{viewname}",
                reverse_kwargs=kwargs,
            )

            assert response.status_code == 200
