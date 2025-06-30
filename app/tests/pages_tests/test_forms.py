import pytest

from grandchallenge.pages.forms import PageCreateForm


@pytest.mark.django_db
@pytest.mark.parametrize(
    "title, valid",
    [
        ("evaluation", False),
        ("💡evaluation", False),
        ("not evaluation", True),
    ],
)
def test_page_create_form_invalid_slug(title, valid):
    form = PageCreateForm(
        data={
            "display_title": title,
            "permission_level": "ALL",
            "hidden": "False",
        },
    )

    assert form.is_valid() == valid
