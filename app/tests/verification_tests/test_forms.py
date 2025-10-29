import pytest

from grandchallenge.profiles.models import BannedEmailAddress
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.forms import (
    ConfirmEmailForm,
    VerificationForm,
)
from tests.factories import UserFactory
from tests.utils import get_view_for_user
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestVerificationForm:
    @pytest.mark.parametrize(
        "email,error",
        (
            (
                "user@mailinator.com",
                "Email addresses hosted by mailinator.com cannot be used.",
            ),
            (
                "user@gmail.com",
                "Email hosted on this domain cannot be used for verification, please provide your work, corporate or institutional email.",
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
        form = VerificationForm(
            user=u, data={"email": email, "user": u.pk, "only_account": True}
        )
        assert error in form.errors["__all__"]

    def test_user_cannot_verify_with_banned_email(self):
        u = UserFactory(
            email="test@foo.com", first_name="Jane", last_name="Doe"
        )

        BannedEmailAddress.objects.create(email=u.email)

        form = VerificationForm(
            user=u, data={"email": u.email, "user": u.pk, "only_account": True}
        )
        assert "This email address is not allowed." in form.errors["__all__"]

        form = VerificationForm(
            user=u,
            data={
                "email": u.email.upper(),
                "user": u.pk,
                "only_account": True,
            },
        )
        assert "This email address is not allowed." in form.errors["__all__"]

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
            user=u2,
            data={"email": u1.email, "user": u2.pk, "only_account": True},
        )
        assert "This email is already in use." in form.errors["__all__"]

        form = VerificationForm(
            user=u2,
            data={
                "email": u1.email.upper(),
                "user": u2.pk,
                "only_account": True,
            },
        )
        assert "This email is already in use." in form.errors["__all__"]

    def test_cannot_make_validation_with_other_validation_email(self):
        u = UserFactory(
            email="test@google.com", first_name="Jane", last_name="Doe"
        )
        u.user_profile.institution = "Foo"
        u.user_profile.department = "Bar"
        u.user_profile.country = "US"
        u.user_profile.save()

        v = VerificationFactory(user=u)

        other_user = UserFactory()

        form = VerificationForm(
            user=other_user,
            data={
                "email": v.email,
                "user": other_user.pk,
                "only_account": True,
            },
        )

        assert (
            "This email address is already in use." in form.errors["__all__"]
        )

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
            "profile-update",
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

    def test_user_can_not_verify_other_token(
        self, settings, client, django_capture_on_commit_callbacks
    ):
        settings.task_eager_propagates = (True,)
        settings.task_always_eager = (True,)

        u1 = UserFactory()
        v1 = VerificationFactory(user=u1)

        u2 = UserFactory()

        with django_capture_on_commit_callbacks(execute=True):
            response = get_view_for_user(
                client=client,
                method=client.post,
                viewname="verifications:confirm",
                reverse_kwargs={"token": v1.token},
                user=u2,
            )

        assert response.status_code == 200
        assert ["Token is invalid"] == response.context["form"].errors["token"]

        u1.refresh_from_db()
        u2.refresh_from_db()
        v1.refresh_from_db()

        assert u1.is_active is True
        assert u2.is_active is False
        assert v1.is_verified is None
