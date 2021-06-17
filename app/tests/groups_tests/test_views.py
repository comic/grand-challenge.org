import pytest
from lxml.html.diff import html_escape

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import (
    UserFactory,
    WorkstationFactory,
)
from tests.organizations_tests.factories import OrganizationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestGroupManagementViews:
    @pytest.mark.parametrize(
        "factory,namespace,view_name,group_attr",
        (
            (OrganizationFactory, "organizations", "members", "members_group"),
            (OrganizationFactory, "organizations", "editors", "editors_group"),
            (AlgorithmFactory, "algorithms", "users", "users_group"),
            (AlgorithmFactory, "algorithms", "editors", "editors_group"),
            (ArchiveFactory, "archives", "users", "users_group"),
            (ArchiveFactory, "archives", "uploaders", "uploaders_group"),
            (ArchiveFactory, "archives", "editors", "editors_group"),
            (ReaderStudyFactory, "reader-studies", "readers", "readers_group"),
            (ReaderStudyFactory, "reader-studies", "editors", "editors_group"),
            (WorkstationFactory, "workstations", "users", "users_group"),
            (WorkstationFactory, "workstations", "editors", "editors_group"),
        ),
    )
    def test_group_management(
        self, client, factory, namespace, view_name, group_attr
    ):
        o = factory()
        group = getattr(o, group_attr)

        admin = UserFactory()
        u = UserFactory()

        assert not group.user_set.filter(pk=u.pk).exists()

        def get_user_autocomplete():
            return get_view_for_user(
                client=client,
                viewname="users-autocomplete",
                user=admin,
                data={"q": u.username.lower()},
            )

        o.add_editor(admin)

        response = get_user_autocomplete()
        assert response.status_code == 200
        assert str(u.pk) in response.json()["results"][0]["id"]
        assert (
            html_escape(str(u.user_profile.get_mugshot_url()))
            in response.json()["results"][0]["text"]
        )
        assert u.username in response.json()["results"][0]["text"]
        assert u.get_full_name() in response.json()["results"][0]["text"]

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


@pytest.mark.django_db
class TestAutocompleteViews:
    @pytest.mark.parametrize(
        "is_verified", (False, True),
    )
    @pytest.mark.parametrize(
        "filter", (("username"), ("email"), ("full_name"),),
    )
    def test_autocomplete_filter_options(self, client, filter, is_verified):
        archive = ArchiveFactory()

        admin = UserFactory()
        archive.add_editor(admin)
        first_name = "Jane"
        last_name = "Doe"

        if is_verified:
            u = UserFactory()
            VerificationFactory(user=u, is_verified=True)
            u.first_name = first_name
            u.last_name = last_name
            u.save()

        else:
            u = UserFactory(first_name=first_name, last_name=last_name)

        u.full_name = u.get_full_name().title()
        filter_criterion = getattr(u, filter)

        def get_user_autocomplete():
            return get_view_for_user(
                client=client,
                viewname="users-autocomplete",
                user=admin,
                data={"q": filter_criterion},
            )

        response = get_user_autocomplete()
        assert response.status_code == 200

        assert str(u.pk) in response.json()["results"][0]["id"]
        assert (
            html_escape(str(u.user_profile.get_mugshot_url()))
            in response.json()["results"][0]["text"]
        )
        assert u.username in response.json()["results"][0]["text"]
        assert u.get_full_name() in response.json()["results"][0]["text"]
        if is_verified:
            assert (
                u.verification.email.split("@")[1]
                in response.json()["results"][0]["text"]
            )

    def test_autocomplete_for_verified_email(self, client):
        archive = ArchiveFactory()
        admin = UserFactory()
        archive.add_editor(admin)

        user = UserFactory()
        VerificationFactory(user=user, is_verified=True)

        response = get_view_for_user(
            client=client,
            viewname="users-autocomplete",
            user=admin,
            data={"q": user.verification.email},
        )
        assert response.status_code == 200

        assert str(user.pk) in response.json()["results"][0]["id"]
