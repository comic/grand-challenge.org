import pytest

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestGroupManagementViews:
    @pytest.mark.parametrize(
        "factory,namespace,view_name,group_attr",
        (
            (OrganizationFactory, "organizations", "members", "members_group"),
            (OrganizationFactory, "organizations", "editors", "editors_group"),
            (AlgorithmFactory, "algorithms", "users", "users_group"),
            (AlgorithmFactory, "algorithms", "editors", "editors_group"),
        ),
    )
    def test_group_management(
        self, client, factory, namespace, view_name, group_attr
    ):
        o = factory()
        group = getattr(o, group_attr)

        admin = UserFactory()
        o.add_editor(admin)

        u = UserFactory()

        assert not group.user_set.filter(pk=u.pk).exists()

        response = get_view_for_user(
            client=client,
            viewname=f"{namespace}:{view_name}-update",
            reverse_kwargs={"slug": o.slug},
            user=admin,
            method=client.post,
            data={"action": "ADD", "user": u.pk},
        )
        assert response.status_code == 302
        assert group.user_set.filter(pk=u.pk).exists()

        response = get_view_for_user(
            client=client,
            viewname=f"{namespace}:{view_name}-update",
            reverse_kwargs={"slug": o.slug},
            user=admin,
            method=client.post,
            data={"action": "REMOVE", "user": u.pk},
        )
        assert response.status_code == 302
        assert not group.user_set.filter(pk=u.pk).exists()
