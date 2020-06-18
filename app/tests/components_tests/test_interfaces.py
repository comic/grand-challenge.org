import pytest
from django.db import IntegrityError

from grandchallenge.components.models import ComponentInterface
from tests.components_tests.factories import ComponentInterfaceFactory


@pytest.mark.parametrize(
    "title",
    [
        "Medical Image",
        "Many Medical Images",
        "Metrics JSON File",
        "Results JSON File",
        "Predictions CSV File",
        "Predictions ZIP File",
    ],
)
@pytest.mark.django_db
def test_default_interfaces_initialised(title):
    interface = ComponentInterface.objects.get(title=title)
    assert interface


@pytest.mark.django_db
def test_relative_path_unique():
    _ = ComponentInterfaceFactory(relative_path="foo")

    with pytest.raises(IntegrityError):
        _ = ComponentInterfaceFactory(relative_path="foo")
