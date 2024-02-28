import pytest

from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.forms import (
    ConfirmEmailForm,
    VerificationForm,
)
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestVerificationForm:
    @pytest.mark.parametrize(
        "email,error",
        (
            (
                "user@mailinator.com",
                "Email hosted by mailinator.com cannot be used for verification due to abuse. Please send an email to support@grand-challenge.org with your user name, institutional email address and a link to your Google Scholar account, lab page, research gate profile or similar so your email address can be verified.",
            ),
            (
                "user@gmail.com",
                "Email hosted by gmail.com cannot be used for verification, please provide your work, corporate or institutional email.",
            ),
        ),
    )
    def test_email_domain(self, email, error):
        u = UserFactory(
            email="test@google.com", first_name="Jane", last_name="Doe"
        )
        u.user_profile.institution = "Foo"
        u.user_profile.department = "Bar"
        u.user_profile.country = "US"
        u.user_profile.save()
        form = VerificationForm(user=u, data={"email": email})
        assert [error] == form.errors["email"]

    def test_can_make_validation_with_own_email(self):
        u = UserFactory(
            email="test@google.com", first_name="Jane", last_name="Doe"
        )
        u.user_profile.institution = "Foo"
        u.user_profile.department = "Bar"
        u.user_profile.country = "US"
        u.user_profile.save()
        form = VerificationForm(
            user=u, data={"email": u.email, "user": u.pk, "only_account": True}
        )
        assert form.is_valid()

        form = VerificationForm(
            user=u,
            data={
                "email": u.email.upper(),
                "user": u.pk,
                "only_account": True,
            },
        )
        assert form.is_valid()

    def test_cannot_make_validation_with_someone_elses_email(self):
        u1 = UserFactory(email="test@google.com")
        u2 = UserFactory(first_name="Jane", last_name="Doe")
        u2.user_profile.institution = "Foo"
        u2.user_profile.department = "Bar"
        u2.user_profile.country = "US"
        u2.user_profile.save()

        form = VerificationForm(
            user=u2, data={"email": u1.email, "user": u2.pk}
        )
        assert ["This email is already in use"] == form.errors["email"]

        form = VerificationForm(
            user=u2, data={"email": u1.email.upper(), "user": u2.pk}
        )
        assert ["This email is already in use"] == form.errors["email"]

    def test_cannot_make_validation_with_other_validation_email(self):
        u = UserFactory(
            email="test@google.com", first_name="Jane", last_name="Doe"
        )
        u.user_profile.institution = "Foo"
        u.user_profile.department = "Bar"
        u.user_profile.country = "US"
        u.user_profile.save()
        v = VerificationFactory(user=u)
        form = VerificationForm(user=UserFactory(), data={"email": v.email})

        assert ["This email is already in use"] == form.errors["email"]

    def test_can_only_create_one_validation(self):
        u = UserFactory(
            email="test@google.com", first_name="Jane", last_name="Doe"
        )
        u.user_profile.institution = "Foo"
        u.user_profile.department = "Bar"
        u.user_profile.country = "US"
        u.user_profile.save()
        VerificationFactory(user=u)
        form = VerificationForm(user=u, data={"email": u.email, "user": u})

        assert [
            "You have already made a verification request. You can check the status of that request <a href='https://testserver/verifications/'>here</a>."
        ] == form.errors["__all__"]

    def test_can_only_create_verification_request_with_complete_profile(self):
        u = UserFactory(email="test@google.com")
        form = VerificationForm(user=u, data={"email": u.email, "user": u})
        profile_link = reverse(
            "profile-update", kwargs={"username": u.username}
        )
        assert [
            f"Your profile information is incomplete. You can complete your profile <a href={profile_link!r}>here</a>."
        ] == form.errors["__all__"]


@pytest.mark.django_db
class TestConfirmEmailForm:
    def test_user_can_verify(self):
        user = UserFactory()
        verification = VerificationFactory(user=user)
        form = ConfirmEmailForm(
            user=user,
            token=verification.token,
            data={"token": verification.token},
        )

        assert form.is_valid()

    def test_user_can_not_verify_other_token(self, settings):
        settings.task_eager_propagates = (True,)
        settings.task_always_eager = (True,)

        u1 = UserFactory()
        v1 = VerificationFactory(user=u1)

        u2 = UserFactory()

        form = ConfirmEmailForm(
            user=u2, token=v1.token, data={"token": v1.token}
        )

        assert not form.is_valid()
        assert ["Token is invalid"] == form.errors["token"]

        u1.refresh_from_db()
        u2.refresh_from_db()
        v1.refresh_from_db()

        assert u1.is_active is True
        assert u2.is_active is False
        assert v1.is_verified is None
