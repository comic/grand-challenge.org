import factory.django
import pytest
from django.core.exceptions import ValidationError
from factory.fuzzy import FuzzyChoice

from grandchallenge.components.form_fields import (
    FlexibleFileField,
    InterfaceFormFieldFactory,
)
from grandchallenge.components.models import InterfaceKind
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
        user=user,
        interface=ci,
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
        user=user,
        interface=ci,
    )
    upload1 = UserUploadFactory(creator=user)
    upload1.status = UserUpload.StatusChoices.COMPLETED
    upload1.save()
    upload2 = UserUploadFactory()
    upload2.status = UserUpload.StatusChoices.COMPLETED
    upload2.save()

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
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.inputs.set([civ1])
    job_without_perm.inputs.set([civ2])
    field = FlexibleFileField(
        user=user,
        interface=ci,
    )

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
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)
    job_with_perm.outputs.set([civ1])
    job_without_perm.outputs.set([civ2])
    field = FlexibleFileField(
        user=user,
        interface=ci,
    )

    parsed_value_for_file_with_permission = field.widget.value_from_datadict(
        data={ci.slug: civ1.pk}, name=ci.slug, files={}
    )
    decompressed_value_for_file_with_permission = field.widget.decompress(
        civ1.pk
    )
    assert (
        parsed_value_for_file_with_permission
        == decompressed_value_for_file_with_permission
        == [civ1.pk, None]
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
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    rs1, rs2 = ReaderStudyFactory.create_batch(2)
    rs1.add_editor(user)
    display_set_with_perm = DisplaySetFactory(reader_study=rs1)
    display_set_without_perm = DisplaySetFactory(reader_study=rs2)
    display_set_with_perm.values.add(civ1)
    display_set_without_perm.values.add(civ2)
    field = FlexibleFileField(
        user=user,
        interface=ci,
    )

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
    civ1, civ2 = ComponentInterfaceValueFactory.create_batch(2, interface=ci)
    a1, a2 = ArchiveFactory.create_batch(2)
    a1.add_editor(user)
    archive_item_with_perm = ArchiveItemFactory(archive=a1)
    archive_item_without_perm = ArchiveItemFactory(archive=a2)
    archive_item_with_perm.values.set([civ1])
    archive_item_without_perm.values.set([civ2])
    field = FlexibleFileField(
        user=user,
        interface=ci,
    )

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
@pytest.mark.parametrize(
    "ci_kind, initial_pk",
    [
        (FuzzyChoice(InterfaceKind.interface_type_file()), "abc"),
        (InterfaceKind.InterfaceKindChoices.MHA_OR_TIFF_IMAGE, "999"),
    ],
)
def test_interface_form_field_factory_wrong_pk_type(ci_kind, initial_pk):
    user = UserFactory()
    ci = ComponentInterfaceFactory(kind=ci_kind)

    with pytest.raises(ValidationError) as e:
        InterfaceFormFieldFactory(interface=ci, user=user, initial=initial_pk)
    assert str(e.value) == f"['“{initial_pk}” is not a valid UUID.']"


@pytest.mark.django_db
def test_flexible_file_widget_prepopulated_value_algorithm_job():
    creator, user = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, file=factory.django.FileField()
    )
    job = AlgorithmJobFactory(creator=creator, time_limit=60)
    job.inputs.set([civ])

    field = InterfaceFormFieldFactory(interface=ci, user=creator, initial=civ)
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=creator, initial=civ.pk
    )
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ.pk)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None


@pytest.mark.django_db
def test_flexible_file_widget_prepopulated_value_display_set():
    editor, user = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, file=factory.django.FileField()
    )
    display_set = DisplaySetFactory()
    display_set.reader_study.add_editor(editor)
    display_set.values.set([civ])

    field = InterfaceFormFieldFactory(interface=ci, user=editor, initial=civ)
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=editor, initial=civ.pk
    )
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ.pk)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None


@pytest.mark.django_db
def test_flexible_file_widget_prepopulated_value_archive_item():
    editor, user = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    civ = ComponentInterfaceValueFactory(
        interface=ci, file=factory.django.FileField()
    )
    archive_item = ArchiveItemFactory()
    archive_item.archive.add_editor(editor)
    archive_item.values.set([civ])

    field = InterfaceFormFieldFactory(interface=ci, user=editor, initial=civ)
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(
        interface=ci, user=editor, initial=civ.pk
    )
    assert field.widget.attrs["current_value"] == civ
    assert field.initial == civ.pk

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=civ.pk)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None


@pytest.mark.django_db
def test_flexible_file_widget_prepopulated_value_user_upload():
    creator, user = UserFactory.create_batch(2)
    ci = ComponentInterfaceFactory(
        kind=FuzzyChoice(InterfaceKind.interface_type_file())
    )
    upload = UserUploadFactory(creator=creator)
    initial = str(upload.pk)

    field = InterfaceFormFieldFactory(
        interface=ci, user=creator, initial=initial
    )
    assert field.widget.attrs["current_value"] == upload
    assert field.initial == initial

    field = InterfaceFormFieldFactory(interface=ci, user=user, initial=initial)
    assert field.widget.attrs["current_value"] is None
    assert field.initial is None
