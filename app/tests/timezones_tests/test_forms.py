from grandchallenge.timezones.forms import TimezoneForm


def test_no_timezone():
    form = TimezoneForm(data={"timzone": "Europe/Amsterdam"})
    assert form.is_valid() is False
    assert form.errors == {"timezone": ["This field is required."]}


def test_valid_timezone():
    form = TimezoneForm(data={"timezone": "Europe/Amsterdam"})
    assert form.is_valid() is True
    assert form.errors == {}


def test_invalid_timezone():
    form = TimezoneForm(data={"timezone": "Europe/Rotterdam"})
    assert form.is_valid() is False
    assert form.errors == {
        "timezone": [
            "Select a valid choice. Europe/Rotterdam is not one of the available choices."
        ]
    }
