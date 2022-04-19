import pytest

from grandchallenge.algorithms.admin import AlgorithmAdmin
from tests.components_tests.factories import ComponentInterfaceFactory


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    form = AlgorithmAdmin.form(data={"inputs": [i.pk], "outputs": [i.pk]})
    assert form.is_valid() is False
    assert "The sets of Inputs and Outputs must be unique" in str(form.errors)
