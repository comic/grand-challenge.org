import pytest
from django.forms import Form

from grandchallenge.core.forms import (
    UniqueTitleCreateFormMixin,
    UniqueTitleUpdateFormMixin,
)
from grandchallenge.reader_studies.models import DisplaySet
from tests.reader_studies_tests.factories import DisplaySetFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_class",
    (UniqueTitleCreateFormMixin, UniqueTitleUpdateFormMixin),
)
@pytest.mark.parametrize(
    "existing_title,new_title,expected_validity",
    (
        ("", "", True),
        ("Foo", "", True),
        ("", "Bar", True),
        ("Foo", "Bar", True),
        ("Foo", "Foo", False),
    ),
)
def test_unique_title_mixin(
    form_class, existing_title, new_title, expected_validity
):

    class TestForm(form_class, Form):

        model = DisplaySet  # For ease, use an existing model with a title

        def __init__(self, *args, instance, **kwargs):
            self.instance = instance

            super().__init__(*args, **kwargs)

    # Create an existing item
    DisplaySetFactory(title=existing_title)

    # Adapt for updating
    instance = None
    if form_class == UniqueTitleUpdateFormMixin:
        instance = DisplaySetFactory()

    form = TestForm(
        instance=instance,
        data={
            "title": new_title,
        },
    )

    assert form.is_valid() is expected_validity
