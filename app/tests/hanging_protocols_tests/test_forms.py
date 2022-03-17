import pytest

from grandchallenge.hanging_protocols.forms import ImagePortMappingMixin
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.hanging_protocols_tests.factories import HangingProtocolFactory


class DummyForm(ImagePortMappingMixin):
    cleaned_data = {"hanging_protocol": None}
    errors = {"image_port_mapping": []}

    def add_error(self, *, field, error):
        self.errors[field].append(error)


@pytest.mark.django_db
def test_image_port_mapping_mixin():
    form = DummyForm()
    form.cleaned_data["image_port_mapping"] = {"main": ["test"]}
    form.clean_image_port_mapping()

    assert (
        "Please select a hanging protocol before filling this field."
        in form.errors["image_port_mapping"]
    )
    assert (
        "Unkown slugs in image_port_mapping: test"
        in form.errors["image_port_mapping"]
    )

    form.errors = {"image_port_mapping": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["image_port_mapping"] = {"secondary": ["test"]}
    form.clean_image_port_mapping()

    assert (
        "Image ports in image_port_mapping do not match those in the selected hanging protocol."
        in form.errors["image_port_mapping"]
    )
    assert (
        "Unkown slugs in image_port_mapping: test"
        in form.errors["image_port_mapping"]
    )

    ComponentInterfaceFactory(title="Test")
    form.errors = {"image_port_mapping": []}
    form.cleaned_data["hanging_protocol"] = HangingProtocolFactory(
        json=[{"viewport_name": "main"}]
    )
    form.cleaned_data["image_port_mapping"] = {"main": ["test"]}
    form.clean_image_port_mapping()

    assert form.errors["image_port_mapping"] == []
