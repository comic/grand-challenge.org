import pytest

from grandchallenge.evaluation.admin import PhaseAdmin
from tests.components_tests.factories import ComponentInterfaceFactory


@pytest.mark.django_db
def test_disjoint_interfaces():
    i = ComponentInterfaceFactory()
    form = PhaseAdmin.form(
        data={"algorithm_inputs": [i.pk], "algorithm_outputs": [i.pk]}
    )
    assert form.is_valid() is False
    assert (
        "The sets of Algorithm Inputs and Algorithm Outputs must be unique"
        in str(form.errors)
    )
