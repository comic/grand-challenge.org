import pytest

from grandchallenge.serving.models import (
    get_component_interface_values_for_user,
)
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_get_component_interface_values_for_user():
    user = UserFactory()
    assert list(get_component_interface_values_for_user(user=user)) == []

    ci = ComponentInterfaceFactory()

    civ1, civ2, civ3, civ4, civ5, civ6, civ7, civ8 = (
        ComponentInterfaceValueFactory.create_batch(8, interface=ci)
    )

    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)

    job_with_perm.inputs.set([civ1])
    job_without_perm.inputs.set([civ2])
    job_with_perm.outputs.set([civ3])
    job_without_perm.outputs.set([civ4])

    rs = ReaderStudyFactory()
    rs.add_editor(user)
    ds_with_perm = DisplaySetFactory(reader_study=rs)
    ds_without_perm = DisplaySetFactory()

    ds_with_perm.values.set([civ5])
    ds_without_perm.values.set([civ6])

    archive = ArchiveFactory()
    archive.add_editor(user)
    ai_with_perm = ArchiveItemFactory(archive=archive)
    ai_without_perm = ArchiveItemFactory()

    ai_with_perm.values.set([civ7])
    ai_without_perm.values.set([civ8])

    assert civ1 in get_component_interface_values_for_user(user=user)
    assert civ3 in get_component_interface_values_for_user(user=user)
    assert civ5 in get_component_interface_values_for_user(user=user)
    assert civ7 in get_component_interface_values_for_user(user=user)
    assert civ2 not in get_component_interface_values_for_user(user=user)
    assert civ4 not in get_component_interface_values_for_user(user=user)
    assert civ6 not in get_component_interface_values_for_user(user=user)
    assert civ8 not in get_component_interface_values_for_user(user=user)
