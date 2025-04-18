import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import Image
from grandchallenge.core.guardian import get_object_if_allowed
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
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "model, factory, codename",
    [
        (Image, ImageFactory, "view_image"),
        (UserUpload, UserUploadFactory, "change_userupload"),
    ],
)
def test_get_object_if_allowed(model, factory, codename):
    user_with_perm, user_without_perm = UserFactory.create_batch(2)
    obj = factory()
    assign_perm(codename, user_with_perm, obj)

    assert (
        get_object_if_allowed(
            model=model, pk=obj.pk, user=user_with_perm, codename=codename
        )
        == obj
    )
    assert (
        get_object_if_allowed(
            model=model, pk=obj.pk, user=user_without_perm, codename=codename
        )
        is None
    )


@pytest.mark.django_db
def test_get_object_if_allowed_upload():
    creator, user = UserFactory.create_batch(2)
    codename = "change_userupload"
    upload = UserUploadFactory(creator=creator)

    assert (
        get_object_if_allowed(
            model=UserUpload, pk=upload.pk, user=creator, codename=codename
        )
        == upload
    )
    assert (
        get_object_if_allowed(
            model=UserUpload, pk=upload.pk, user=user, codename=codename
        )
        is None
    )


@pytest.mark.django_db
def test_get_component_interface_values_for_user():
    user = UserFactory()
    assert set(get_component_interface_values_for_user(user=user)) == set()

    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)

    civ1, civ2, civ3, civ4, civ5, civ6, civ7, civ8 = (
        ComponentInterfaceValueFactory.create_batch(8, interface=ci1)
    )
    civ9, civ10, civ11, civ12, civ13, civ14, civ15, civ16 = (
        ComponentInterfaceValueFactory.create_batch(8, interface=ci2)
    )

    job_with_perm = AlgorithmJobFactory(creator=user, time_limit=60)
    job_without_perm = AlgorithmJobFactory(time_limit=60)

    job_with_perm.inputs.set([civ1, civ9])
    job_without_perm.inputs.set([civ2, civ10])
    job_with_perm.outputs.set([civ3, civ11])
    job_without_perm.outputs.set([civ4, civ12])

    rs = ReaderStudyFactory()
    rs.add_editor(user)
    ds_with_perm = DisplaySetFactory(reader_study=rs)
    ds_without_perm = DisplaySetFactory()

    ds_with_perm.values.set([civ5, civ13])
    ds_without_perm.values.set([civ6, civ14])

    archive = ArchiveFactory()
    archive.add_editor(user)
    ai_with_perm = ArchiveItemFactory(archive=archive)
    ai_without_perm = ArchiveItemFactory()

    ai_with_perm.values.set([civ7, civ15])
    ai_without_perm.values.set([civ8, civ16])

    assert set(get_component_interface_values_for_user(user=user)) == {
        civ1,
        civ3,
        civ5,
        civ7,
        civ9,
        civ11,
        civ13,
        civ15,
    }

    # subset by interface
    assert set(
        get_component_interface_values_for_user(user=user, interface=ci1)
    ) == {civ1, civ3, civ5, civ7}
    assert set(
        get_component_interface_values_for_user(user=user, interface=ci2)
    ) == {civ9, civ11, civ13, civ15}

    # subset by civ pk
    assert set(
        get_component_interface_values_for_user(user=user, civ_pk=civ1.pk)
    ) == {civ1}
    assert set(
        get_component_interface_values_for_user(user=user, civ_pk=civ9.pk)
    ) == {civ9}
    assert (
        set(get_component_interface_values_for_user(user=user, civ_pk=civ2.pk))
        == set()
    )
