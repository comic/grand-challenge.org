import pytest
from allauth.account.models import EmailAddress
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.profiles.views import UserProfileViewSet
from grandchallenge.subdomains.utils import reverse
from tests.factories import PolicyFactory, UserFactory


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
        response = UserProfileViewSet.as_view(actions={"get": "list"})(request)
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "permission", (True, False),
    )
    def test_profile_self(self, rf, permission):
        user = UserFactory()
        url = reverse("api:profiles-user-self")
        request = rf.get(url)
        force_authenticate(request, user=user)
        if permission:
            assign_perm("view_profile", user, user.user_profile)
        response = UserProfileViewSet.as_view(actions={"get": "self"})(request)
        if permission:
            assert response.status_code == 200
            assert response.data["user"] == {
                "username": user.username
            }  # no user id
            for field in (
                "mugshot",
                "privacy",
                "institution",
                "department",
                "location",
                "website",
            ):
                assert field in response.data
            assert "country" not in response.data
        else:
            assert response.status_code == 403

    @pytest.mark.parametrize(
        "user_kwargs,permission, expected_count",
        (
            (None, False, 0),
            ({}, False, 0),
            ({"is_staff": True}, False, 0),
            ({"is_superuser": True}, False, 5),
            (None, True, 0),
            ({}, True, 1),
            ({"is_staff": True}, True, 1),
            ({"is_superuser": True}, True, 5),
        ),
    )
    def test_profiles_list_permissions(
        self, rf, user_kwargs, permission, expected_count
    ):
        user = None
        if user_kwargs is not None:
            user = UserFactory(**user_kwargs)
        UserFactory()
        UserFactory()
        url = reverse("api:profiles-user-list")
        request = rf.get(url)
        if user is not None:
            force_authenticate(request, user=user)

        if user is not None and permission:
            assign_perm("view_profile", user, user.user_profile)
        response = UserProfileViewSet.as_view(actions={"get": "list"})(request)
        if user:
            assert response.status_code == 200
            assert response.data["count"] == expected_count
        else:
            assert response.status_code == 401

    @pytest.mark.parametrize(
        "permission", (True, False),
    )
    def test_profiles_retrieve_permissions(self, rf, permission):
        user = UserFactory()
        kwargs = {"pk": user.user_profile.pk}
        url = reverse("api:profiles-user-detail", kwargs=kwargs)
        request = rf.get(url)
        force_authenticate(request, user=user)
        if permission:
            assign_perm("view_profile", user, user.user_profile)
        response = UserProfileViewSet.as_view(actions={"get": "retrieve"})(
            request, **kwargs
        )
        if permission:
            assert response.status_code == 200
            assert response.data["user"]["username"] == user.username
        else:
            assert response.status_code == 404
