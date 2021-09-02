import pytest

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
                "Email hosted by mailinator.com cannot be used for verification due to abuse. Please contact support to verify your account another way.",
            ),
            (
                "user@gmail.com",
                "Email hosted by gmail.com cannot be used for verification, please provide your work, corporate or institutional email.",
            ),
        ),
    )
    def test_email_domain(self, email, error):
        form = VerificationForm(user=UserFactory(), data={"email": email})

        assert [error] == form.errors["email"]

    def test_can_make_validation_with_own_email(self):
        u = UserFactory(email="test@google.com")

        form = VerificationForm(user=u, data={"email": u.email, "user": u.pk})
        assert form.is_valid()

        form = VerificationForm(
            user=u, data={"email": u.email.upper(), "user": u.pk}
        )
        assert form.is_valid()

    def test_cannot_make_validation_with_someone_elses_email(self):
        u1 = UserFactory(email="test@google.com")
        u2 = UserFactory()

        form = VerificationForm(
            user=u2, data={"email": u1.email, "user": u2.pk}
        )
        assert ["This email is already in use"] == form.errors["email"]

        form = VerificationForm(
            user=u2, data={"email": u1.email.upper(), "user": u2.pk}
        )
        assert ["This email is already in use"] == form.errors["email"]

    def test_cannot_make_validation_with_other_validation_email(self):
        u = UserFactory()
        v = VerificationFactory(user=u)
        form = VerificationForm(user=UserFactory(), data={"email": v.email})

        assert ["This email is already in use"] == form.errors["email"]

    def test_can_only_create_one_validation(self):
        u = UserFactory()
        VerificationFactory(user=u)
        form = VerificationForm(user=u, data={"email": u.email, "user": u})

        assert ["You have already made a verification request"] == form.errors[
            "__all__"
        ]


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

    def test_user_can_not_verify_other_token(self):
        u1 = UserFactory()
        v1 = VerificationFactory(user=u1)

        u2 = UserFactory()
        VerificationFactory(user=u2)

        form = ConfirmEmailForm(
            user=u2, token=v1.token, data={"token": v1.token},
        )

        assert not form.is_valid()
        assert ["Token is invalid"] == form.errors["token"]
