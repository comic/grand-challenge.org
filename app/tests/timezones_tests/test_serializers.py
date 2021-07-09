from rest_framework.exceptions import ErrorDetail

from grandchallenge.timezones.serializers import TimezoneSerializer


def test_no_timezone():
    form = TimezoneSerializer(data={"timzone": "Europe/Amsterdam"})
    assert form.is_valid() is False
    assert form.errors == {"timezone": ["This field is required."]}


def test_valid_timezone():
    form = TimezoneSerializer(data={"timezone": "Europe/Amsterdam"})
    assert form.is_valid() is True
    assert form.errors == {}


def test_invalid_timezone():
    form = TimezoneSerializer(data={"timezone": "Europe/Rotterdam"})
    assert form.is_valid() is False
    assert form.errors == {
        "timezone": [
            ErrorDetail(
                string='"Europe/Rotterdam" is not a valid choice.',
                code="invalid_choice",
            )
        ]
    }
