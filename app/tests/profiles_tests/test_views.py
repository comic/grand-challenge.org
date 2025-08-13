import random
import string

import pytest
from allauth.account.models import EmailAddress
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.test import force_authenticate

from grandchallenge.profiles.admin import User
from grandchallenge.profiles.models import NotificationEmailOptions
from grandchallenge.profiles.views import UserProfileViewSet
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import VerificationUserSet
from tests.factories import PolicyFactory, UserFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
class TestSignInRedirect:
    def get_redirect_response(self, client, next=None):
        password = get_random_string(32)

        self.user = UserFactory(password=password)

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
            data={
                "first_name": "Firstname",
                "last_name": "Lastname",
                "institution": "Institution",
                "department": "Department",
                "country": "NL",
                "display_organizations": False,
                "notification_email_choice": NotificationEmailOptions.DAILY_SUMMARY,
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


@pytest.mark.parametrize(
    "viewname",
    ("newsletter-unsubscribe", "notification-unsubscribe"),
)
@pytest.mark.django_db
def test_one_click_unsubscribe_invalid_token(client, viewname):
    user = UserFactory()

    valid_token = user.user_profile.unsubscribe_token
    invalid_token = "".join(
        random.choices(string.ascii_letters + string.digits + "_-", k=20)
    )

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"token": valid_token},
    )
    assert response.status_code == 200

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"token": invalid_token},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "logged_in,notification_preference",
    (
        (
            False,
            NotificationEmailOptions.DAILY_SUMMARY,
        ),
        (
            True,
            NotificationEmailOptions.DAILY_SUMMARY,
        ),
        (
            True,
            NotificationEmailOptions.INSTANT,
        ),
        (
            False,
            NotificationEmailOptions.INSTANT,
        ),
    ),
)
@pytest.mark.django_db
def test_one_click_unsubscribe_functionality_for_notifications(
    client,
    logged_in,
    notification_preference,
):
    user = UserFactory()
    user.user_profile.notification_email_choice = notification_preference
    user.user_profile.save()
    assert user.user_profile.receive_newsletter is None

    token = user.user_profile.unsubscribe_token
    response = get_view_for_user(
        client=client,
        viewname="notification-unsubscribe",
        reverse_kwargs={"token": token},
        method=client.post,
        user=user if logged_in else None,
    )
    assert response.status_code == 302
    user.user_profile.refresh_from_db()
    assert (
        user.user_profile.notification_email_choice
        == NotificationEmailOptions.DISABLED
    )
    # newsletter preference remains unchanged
    assert user.user_profile.receive_newsletter is None
    assert VerificationUserSet.objects.count() == 0


@pytest.mark.parametrize("logged_in", [True, False])
@pytest.mark.django_db
def test_one_click_unsubscribe_functionality_for_newsletter(
    client,
    logged_in,
):
    user = UserFactory()
    user.user_profile.receive_newsletter = True
    user.user_profile.save()
    assert (
        user.user_profile.notification_email_choice
        == NotificationEmailOptions.DAILY_SUMMARY
    )

    token = user.user_profile.unsubscribe_token
    response = get_view_for_user(
        client=client,
        viewname="newsletter-unsubscribe",
        reverse_kwargs={"token": token},
        method=client.post,
        user=user if logged_in else None,
    )
    assert response.status_code == 302
    user.user_profile.refresh_from_db()
    assert not user.user_profile.receive_newsletter
    # notification preference remains unchanged
    assert (
        user.user_profile.notification_email_choice
        == NotificationEmailOptions.DAILY_SUMMARY
    )
    assert VerificationUserSet.objects.count() == 0


@pytest.mark.parametrize(
    "viewname,subscription_attr,new_subscription_preference",
    (
        ("newsletter-unsubscribe", "receive_newsletter", False),
        (
            "notification-unsubscribe",
            "notification_email_choice",
            NotificationEmailOptions.DISABLED,
        ),
    ),
)
@pytest.mark.django_db
def test_one_click_unsubscribe_user_mismatch(
    client, settings, viewname, subscription_attr, new_subscription_preference
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    user.user_profile.receive_newsletter = True
    user.user_profile.notification_email_choice = (
        NotificationEmailOptions.DAILY_SUMMARY
    )
    user.user_profile.save()

    token = user.user_profile.unsubscribe_token

    other_user = UserFactory()
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname=viewname,
        reverse_kwargs={"token": token},
        user=other_user,
    )
    assert response.status_code == 302
    user.user_profile.refresh_from_db()
    # token owner is unsubscribed
    assert (
        getattr(user.user_profile, subscription_attr)
        == new_subscription_preference
    )
    # token owner and requesting user are added to a verification user set
    user_set = VerificationUserSet.objects.get()
    assert user in user_set.users.all()
    assert other_user in user_set.users.all()


@pytest.mark.django_db
def test_notification_email_choice_after_user_signup(client):

    response = get_view_for_user(
        url="/accounts/signup/",
        client=client,
        method=client.post,
        data={
            "email": "user123@domain.com",
            "email2": "user123@domain.com",
            "username": "user123",
            "first_name": "Firstname",
            "last_name": "Lastname",
            "institution": "Institution",
            "department": "Department",
            "country": "NL",
            "receive_newsletter": False,
            "only_account": True,
            "password1": "ENwfuftURoZgFdq",
            "password2": "ENwfuftURoZgFdq   ",
            "notification_email_choice": NotificationEmailOptions.DISABLED,
        },
    )

    assert response.status_code == 302
    assert response.url == "/accounts/confirm-email/"

    u = User.objects.get(username="user123")
    assert u.user_profile.notification_email_choice == "DISABLED"


@pytest.mark.django_db
def test_policies_must_be_accepted(client):
    PolicyFactory.create_batch(2)

    response = get_view_for_user(
        url="/accounts/signup/",
        client=client,
        method=client.post,
        data={
            "email": "user123@domain.com",
            "email2": "user123@domain.com",
            "username": "user123",
            "first_name": "Firstname",
            "last_name": "Lastname",
            "institution": "Institution",
            "department": "Department",
            "country": "NL",
            "receive_newsletter": False,
            "only_account": True,
            "accept_policy_0": False,
            "password1": "ENwfuftURoZgFdq",
            "password2": "ENwfuftURoZgFdq   ",
            "notification_email_choice": NotificationEmailOptions.DISABLED,
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors == {
        "accept_policy_0": ["This field is required."],
        "accept_policy_1": ["This field is required."],
    }

    response = get_view_for_user(
        url="/accounts/signup/",
        client=client,
        method=client.post,
        data={
            "email": "user123@domain.com",
            "email2": "user123@domain.com",
            "username": "user123",
            "first_name": "Firstname",
            "last_name": "Lastname",
            "institution": "Institution",
            "department": "Department",
            "country": "NL",
            "receive_newsletter": False,
            "only_account": True,
            "accept_policy_0": True,
            "accept_policy_1": True,
            "password1": "ENwfuftURoZgFdq",
            "password2": "ENwfuftURoZgFdq   ",
            "notification_email_choice": NotificationEmailOptions.DISABLED,
        },
    )

    assert response.status_code == 302
