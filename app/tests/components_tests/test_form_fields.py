import pytest
from django.core.exceptions import ValidationError
from factory.fuzzy import FuzzyChoice

from grandchallenge.components.form_fields import FlexibleFileField
from grandchallenge.components.models import InterfaceKind
from grandchallenge.serving.models import (
    get_component_interface_values_for_user,
)
from grandchallenge.uploads.models import UserUpload
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
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_flexible_file_field_validation_empty_data_and_missing_values():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )

    parsed_value_for_empty_data = field.widget.value_from_datadict(
        data={}, name=ci.slug, files={}
    )
    assert parsed_value_for_empty_data == [None, None]

    decompressed_value_for_missing_value = field.widget.decompress(value=None)
    assert decompressed_value_for_missing_value == [None, None]

    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_empty_data)


@pytest.mark.django_db
def test_flexible_file_field_validation_user_uploads():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )
    upload1 = UserUploadFactory(creator=user)
    upload2 = UserUploadFactory()

    parsed_value_for_upload_from_user = field.widget.value_from_datadict(
        data={ci.slug: str(upload1.pk)}, name=ci.slug, files={}
    )
    decompressed_value_for_upload_from_user = field.widget.decompress(
        str(upload1.pk)
    )
    assert (
        parsed_value_for_upload_from_user
        == decompressed_value_for_upload_from_user
        == [None, str(upload1.pk)]
    )
    assert field.clean(parsed_value_for_upload_from_user) == upload1

    parsed_value_from_upload_from_other_user = (
        field.widget.value_from_datadict(
            data={ci.slug: str(upload2.pk)}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_upload_from_other_user = field.widget.decompress(
        str(upload2.pk)
    )
    assert (
        parsed_value_from_upload_from_other_user
        == decompressed_value_for_upload_from_other_user
        == [None, str(upload2.pk)]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_from_upload_from_other_user)


@pytest.mark.django_db
def test_flexible_file_field_validation_with_algorithm_job_inputs():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.inputs.set([civ1])
    job_without_perm.inputs.set([civ2])

    parsed_value_for_file_with_permission = field.widget.value_from_datadict(
        data={ci.slug: civ1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_file_with_permission = field.widget.decompress(
        civ1.pk
    )
    assert (
        parsed_value_for_file_with_permission
        == decompressed_value_for_file_with_permission
        == [
            civ1.pk,
            None,
        ]
    )
    assert field.clean(parsed_value_for_file_with_permission) == civ1

    parsed_value_for_file_without_permission = (
        field.widget.value_from_datadict(
            data={ci.slug: civ2.pk}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_file_without_permission = field.widget.decompress(
        civ2.pk
    )
    assert (
        parsed_value_for_file_without_permission
        == decompressed_value_for_file_without_permission
        == [civ2.pk, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_file_without_permission)


@pytest.mark.django_db
def test_flexible_file_field_validation_with_algorithm_job_outputs():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.outputs.set([civ1])
    job_without_perm.outputs.set([civ2])

    parsed_value_for_file_with_permission = field.widget.value_from_datadict(
        data={ci.slug: civ1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_file_with_permission = field.widget.decompress(
        civ1.pk
    )
    assert (
        parsed_value_for_file_with_permission
        == decompressed_value_for_file_with_permission
        == [
            civ1.pk,
            None,
        ]
    )
    assert field.clean(parsed_value_for_file_with_permission) == civ1

    parsed_value_for_file_without_permission = (
        field.widget.value_from_datadict(
            data={ci.slug: civ2.pk}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_file_without_permission = field.widget.decompress(
        civ2.pk
    )
    assert (
        parsed_value_for_file_without_permission
        == decompressed_value_for_file_without_permission
        == [civ2.pk, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_file_without_permission)


@pytest.mark.django_db
def test_flexible_file_field_validation_with_display_sets():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )

    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    rs1.add_editor(user)
    display_set_with_perm = DisplaySetFactory(reader_study=rs1)
    display_set_without_perm = DisplaySetFactory(reader_study=rs2)
    display_set_with_perm.values.add(civ1)
    display_set_without_perm.values.add(civ2)

    parsed_value_for_file_with_permission = field.widget.value_from_datadict(
        data={ci.slug: civ1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_file_with_permission = field.widget.decompress(
        civ1.pk
    )
    assert (
        parsed_value_for_file_with_permission
        == decompressed_value_for_file_with_permission
        == [
            civ1.pk,
            None,
        ]
    )
    assert field.clean(parsed_value_for_file_with_permission) == civ1

    parsed_value_for_file_without_permission = (
        field.widget.value_from_datadict(
            data={ci.slug: civ2.pk}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_file_without_permission = field.widget.decompress(
        civ2.pk
    )
    assert (
        parsed_value_for_file_without_permission
        == decompressed_value_for_file_without_permission
        == [civ2.pk, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_file_without_permission)


@pytest.mark.django_db
def test_flexible_file_field_validation_with_archive_items():
    user = UserFactory()
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    field = FlexibleFileField(
        file_search_queryset=get_component_interface_values_for_user(
            user=user
        ).filter(interface=ci),
        upload_queryset=UserUpload.objects.filter(creator=user).all(),
    )

    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    a1, a2 = ArchiveFactory.create_batch(2)
    a1.add_editor(user)
    archive_item_with_perm = ArchiveItemFactory(archive=a1)
    archive_item_without_perm = ArchiveItemFactory(archive=a2)
    archive_item_with_perm.values.set([civ1])
    archive_item_without_perm.values.set([civ2])

    parsed_value_for_file_with_permission = field.widget.value_from_datadict(
        data={ci.slug: civ1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_file_with_permission = field.widget.decompress(
        civ1.pk
    )
    assert (
        parsed_value_for_file_with_permission
        == decompressed_value_for_file_with_permission
        == [
            civ1.pk,
            None,
        ]
    )
    assert field.clean(parsed_value_for_file_with_permission) == civ1

    parsed_value_for_file_without_permission = (
        field.widget.value_from_datadict(
            data={ci.slug: civ2.pk}, name=ci.slug, files={}
        )
    )
    decompressed_value_for_file_without_permission = field.widget.decompress(
        civ2.pk
    )
    assert (
        parsed_value_for_file_without_permission
        == decompressed_value_for_file_without_permission
        == [civ2.pk, None]
    )
    with pytest.raises(ValidationError):
        field.clean(parsed_value_for_file_without_permission)
