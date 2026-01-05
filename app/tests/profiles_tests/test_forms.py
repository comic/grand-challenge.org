import pytest

from grandchallenge.profiles.forms import UserProfileForm
from grandchallenge.profiles.models import NotificationEmailOptions
from tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "first_name,last_name,email,expected_errors",
    [
        (
            "John",
            "Doe",
            "john.doe@example.test",
            {},
        ),
        (
            "john.doe@example.test",
            "Doe",
            "john.doe@example.test",
            {"first_name": {"First Name cannot contain your email address"}},
        ),
        (
            "John",
            "john.doe@example.test",
            "john.doe@example.test",
            {"last_name": {"Last Name cannot contain your email address"}},
        ),
        (
            "john.doe@example.test",
            "john.doe@example.test",
            "john.doe@example.test",
            {
                "first_name": {"First Name cannot contain your email address"},
                "last_name": {"Last Name cannot contain your email address"},
            },
        ),
        (
            "123john.doe@example.test",
            "john.doe@example.test123",
            "john.doe@example.test",
            {
                "first_name": {"First Name cannot contain your email address"},
                "last_name": {"Last Name cannot contain your email address"},
            },
        ),
    ],
)
def test_user_profile_form_validation(
    first_name, last_name, email, expected_errors
):
    user = UserFactory(email=email)
    user_profile = user.user_profile

    form_data = {
        "first_name": first_name,
        "last_name": last_name,
        "institution": "Test Institution",
        "department": "Test Department",
        "country": "NL",
        "notification_email_choice": NotificationEmailOptions.DAILY_SUMMARY,
        "receive_newsletter": False,
    }

    form = UserProfileForm(data=form_data, instance=user_profile)
    form.full_clean()

    for field, errors in expected_errors.items():
        assert field in form.errors
        assert set(form.errors[field]) == errors
