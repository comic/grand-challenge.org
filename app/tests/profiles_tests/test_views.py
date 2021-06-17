import pytest
from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.profiles.views import UserProfileViewSet
from grandchallenge.subdomains.utils import reverse
from tests.factories import PolicyFactory, UserFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestSignInRedirect:
    def get_redirect_response(self, client, next=None):
        password = "password"

        self.user = UserFactory()
        self.user.set_password(password)
        self.user.save()

        EmailAddress.objects.create(
            user=self.user, email=self.user.email, verified=True
        )

        url = reverse("account_login")
        if next:
            url += f"?next={next}"

        return client.post(
            url,
            data={"login": self.user.username, "password": password},
            follow=True,
        )

    def test_default_redirect(self, client):
        response = self.get_redirect_response(client)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert reverse("profile-detail-redirect").endswith(
            response.redirect_chain[0][0]
        )
        assert response.status_code == status.HTTP_200_OK

    def test_redirect(self, client):
        expected_url = "/challenges/"
        response = self.get_redirect_response(client, expected_url)
        assert response.redirect_chain[0][1] == status.HTTP_302_FOUND
        assert response.status_code == status.HTTP_200_OK
        assert response.redirect_chain[0][0] == expected_url


@pytest.mark.django_db
class TestUrlEncodedUsername:
    def test_special_username(self, client):
        user = UserFactory(username="tést")
        url = reverse("profile-detail-redirect")
        client.force_login(user)
        response = client.get(url, follow=True)
        assert response.status_code == status.HTTP_200_OK
        assert "t%C3%A9st" in response.redirect_chain[0][0]


@pytest.mark.django_db
def test_terms_form_fields(client):
    p = PolicyFactory(title="terms", body="blah")
    response = client.get(reverse("account_signup"))
    assert response.status_code == 200
    assert p.get_absolute_url() in response.rendered_content


@pytest.mark.django_db
class TestProfileViewSets:
    def test_profile_self_not_logged_in(self, rf):
        UserFactory()
        url = reverse("api:profiles-user-self")
        request = rf.get(url)
        response = UserProfileViewSet.as_view(actions={"get": "self"})(request)
        assert response.status_code == 200
        assert response.data["user"] == {"username": "AnonymousUser"}

    def test_profile_self(self, rf):
        user = UserFactory()
        url = reverse("api:profiles-user-self")
        request = rf.get(url)
        force_authenticate(request, user=user)
        response = UserProfileViewSet.as_view(actions={"get": "self"})(request)
        assert response.status_code == 200
        assert response.data["user"] == {
            "username": user.username
        }  # no user id
        for field in (
            "mugshot",
            "institution",
            "department",
            "location",
            "website",
        ):
            assert field in response.data
        assert "country" not in response.data
        assert user.user_profile.display_organizations

    def test_organization_display(self, client):
        u1 = UserFactory()
        u2 = UserFactory()
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        org1.add_member(u1)

        assert org1.is_member(u1)
        assert not org2.is_member(u1)
        assert not org1.is_member(u2)
        assert not org2.is_member(u2)

        response = get_view_for_user(
            viewname="profile-detail",
            client=client,
            user=u1,
            reverse_kwargs={"username": u1.username},
        )
        assert len(response.context[-1]["organizations"]) == 1
        assert org1.title in response.content.decode()
        assert org2.title not in response.content.decode()

        response = get_view_for_user(
            viewname="profile-detail",
            client=client,
            user=u2,
            reverse_kwargs={"username": u2.username},
        )
        assert len(response.context[-1]["organizations"]) == 0
        assert "Organizations" not in response.content.decode()
        u1.user_profile.display_organizations = False
        u1.user_profile.save()

        response = get_view_for_user(
            viewname="profile-detail",
            client=client,
            user=u1,
            reverse_kwargs={"username": u1.username},
        )

        assert org1.title not in response.content.decode()

    def test_organization_update(self, client):
        u1 = UserFactory()
        org1 = OrganizationFactory()
        org1.add_member(u1)

        response = get_view_for_user(
            viewname="profile-detail",
            client=client,
            user=u1,
            reverse_kwargs={"username": u1.username},
        )

        assert org1.title in response.content.decode()

        _ = get_view_for_user(
            viewname="profile-update",
            client=client,
            method=client.post,
            user=u1,
            reverse_kwargs={"username": u1.username},
            data={
                "first_name": "Firstname",
                "last_name": "Lastname",
                "institution": "Institution",
                "department": "Department",
                "country": "NL",
                "display_organizations": False,
            },
        )

        u1.user_profile.refresh_from_db()

        response = get_view_for_user(
            viewname="profile-detail",
            client=client,
            user=u1,
            reverse_kwargs={"username": u1.username},
        )

        assert org1.title not in response.content.decode()
