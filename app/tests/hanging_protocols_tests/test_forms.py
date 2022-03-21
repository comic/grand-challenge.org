import pytest

from grandchallenge.hanging_protocols.forms import ViewContentMixin
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory


class DummyForm(ViewContentMixin):
    cleaned_data = {"hanging_protocol": None}
    errors = {"view_content": []}

    def add_error(self, *, field, error):
        self.errors[field].append(error)


@pytest.mark.django_db
def test_view_content_mixin():
    form = DummyForm()
    form.cleaned_data["view_content"] = {"main": ["test"]}
    form.clean_view_content()

    assert (
        "Please select a hanging protocol before filling this field."
        in form.errors["view_content"]
    )
    assert "Unkown slugs in view_content: test" in form.errors["view_content"]

    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"secondary": ["test"]}
    form.clean_view_content()

    assert (
        "Image ports in view_content do not match those in the selected hanging protocol."
        in form.errors["view_content"]
    )
    assert "Unkown slugs in view_content: test" in form.errors["view_content"]

    ComponentInterfaceFactory(title="Test")
    form.errors = {"view_content": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["view_content"] = {"main": ["test"]}
    form.clean_view_content()

    assert form.errors["view_content"] == []
