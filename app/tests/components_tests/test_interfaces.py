import pytest
from django.db import IntegrityError

from grandchallenge.components.models import ComponentInterface
from tests.components_tests.factories import ComponentInterfaceFactory


@pytest.mark.parametrize(
    "slug",
    [
        "generic-medical-image",
        "generic-overlay",
        "metrics-json-file",
        "results-json-file",
        "predictions-json-file",
        "predictions-csv-file",
        "predictions-zip-file",
    ],
)
@pytest.mark.django_db
def test_default_interfaces_initialised(slug):
    interface = ComponentInterface.objects.get(slug=slug)
    assert interface


@pytest.mark.django_db
def test_relative_path_unique():
    _ = ComponentInterfaceFactory(relative_path="foo")

    with pytest.raises(IntegrityError):
        _ = ComponentInterfaceFactory(relative_path="foo")
