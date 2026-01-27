import factory.django
import pytest
from django.core.exceptions import ValidationError
from factory.fuzzy import FuzzyChoice

from grandchallenge.components.form_fields import (
    FileSourceChoiceField,
    FileSourceChoices,
)
from grandchallenge.components.forms import (
    INTERFACE_FORM_FIELD_PREFIX,
    FlexibleWidgetPrefixes,
    InterfaceFormFieldsMixin,
)
from grandchallenge.components.models import InterfaceKinds, SourceChoices
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
def test_file_search_field_validation_with_algorithm_job_inputs():
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=FuzzyChoice(InterfaceKinds.file))
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.inputs.set([civ1])
    job_without_perm.inputs.set([civ2])
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", f"{civ1.pk}"]) == civ1
    with pytest.raises(ValidationError):
        field.clean(["", f"{civ2.pk}"])


@pytest.mark.django_db
def test_file_search_field_validation_with_algorithm_job_outputs():
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=FuzzyChoice(InterfaceKinds.file))
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.outputs.set([civ1])
    job_without_perm.outputs.set([civ2])
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", f"{civ1.pk}"]) == civ1
    with pytest.raises(ValidationError):
        field.clean(["", f"{civ2.pk}"])


@pytest.mark.django_db
def test_file_search_field_validation_with_display_sets():
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=FuzzyChoice(InterfaceKinds.file))
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    rs1.add_editor(user)
    display_set_with_perm = DisplaySetFactory(reader_study=rs1)
    display_set_without_perm = DisplaySetFactory(reader_study=rs2)
    display_set_with_perm.values.add(civ1)
    display_set_without_perm.values.add(civ2)
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", f"{civ1.pk}"]) == civ1
    with pytest.raises(ValidationError):
        field.clean(["", f"{civ2.pk}"])


@pytest.mark.django_db
def test_file_search_field_validation_with_archive_items():
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=FuzzyChoice(InterfaceKinds.file))
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    a1, a2 = ArchiveFactory.create_batch(2)
    a1.add_editor(user)
    archive_item_with_perm = ArchiveItemFactory(archive=a1)
    archive_item_without_perm = ArchiveItemFactory(archive=a2)
    archive_item_with_perm.values.set([civ1])
    archive_item_without_perm.values.set([civ2])
    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, user=user
    )[f"{FlexibleWidgetPrefixes.SEARCH}{ci.slug}"]

    assert field.clean(["", f"{civ1.pk}"]) == civ1
    with pytest.raises(ValidationError):
        field.clean(["", f"{civ2.pk}"])


def test_file_source_select_options():
    ci = ComponentInterfaceFactory.build(kind=FuzzyChoice(InterfaceKinds.file))
    civ = ComponentInterfaceValueFactory.build(
        interface=ci, file=factory.django.FileField()
    )

    field = FileSourceChoiceField(current_socket_value=civ)

    assert field.current_socket_value == civ
    assert field.choices == [
        ("CURRENT", civ.title),
        ("SEARCH", "Select an existing file"),
        ("UPLOAD", "Upload a new file"),
        ("REMOVE", "Remove this file"),
    ]
    assert field.clean(SourceChoices.CURRENT) == civ
    assert field.clean(SourceChoices.REMOVE) == SourceChoices.REMOVE
    with pytest.raises(ValidationError, match="This field is required."):
        field.clean(FileSourceChoices.UNDEFINED)

    field = FileSourceChoiceField()

    assert field.choices == [
        ("", "Choose data source..."),
        ("SEARCH", "Select an existing file"),
        ("UPLOAD", "Upload a new file"),
    ]
    assert field.current_socket_value is None
    with pytest.raises(ValidationError, match="Select a valid choice."):
        field.clean(SourceChoices.CURRENT)
    with pytest.raises(ValidationError, match="Select a valid choice."):
        field.clean(SourceChoices.REMOVE.value)
    with pytest.raises(ValidationError, match="This field is required."):
        field.clean(FileSourceChoices.UNDEFINED)


def test_json_field_prepopulated_value():
    ci = ComponentInterfaceFactory.build(kind=FuzzyChoice(InterfaceKinds.json))
    civ = ComponentInterfaceValueFactory.build(interface=ci, value="foobar")

    field = InterfaceFormFieldsMixin().get_fields_for_interface(
        interface=ci, current_socket_value=civ
    )[f"{INTERFACE_FORM_FIELD_PREFIX}{ci.slug}"]

    assert field.initial == "foobar"
