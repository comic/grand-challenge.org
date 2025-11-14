import pytest

from grandchallenge.core.fixtures import create_uploaded_image
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.blogs_tests.factory import PostFactory
from tests.factories import ChallengeFactory, UserFactory, WorkstationFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory

INVALID_IMAGE_COMBINATIONS = {
    ("userprofile", "logo"),
    ("userprofile", "social_image"),
    ("organization", "social_image"),
    ("workstation", "social_image"),
    ("post", "social_image"),
    ("algorithm", "mugshot"),
    ("archive", "mugshot"),
    ("post", "mugshot"),
    ("challenge", "mugshot"),
    ("organization", "mugshot"),
    ("readerstudy", "mugshot"),
    ("workstation", "mugshot"),
    ("algorithm", "banner"),
    ("archive", "banner"),
    ("post", "banner"),
    ("organization", "banner"),
    ("userprofile", "banner"),
    ("readerstudy", "banner"),
    ("workstation", "banner"),
}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name", ("logo", "social_image", "banner", "mugshot")
)
@pytest.mark.parametrize(
    "factory",
    (
        AlgorithmFactory,
        ArchiveFactory,
        PostFactory,
        ChallengeFactory,
        OrganizationFactory,
        lambda: UserFactory().user_profile,
        ReaderStudyFactory,
        WorkstationFactory,
    ),
)
def test_height_width_set_on_creation(
    uploaded_image, field_name, factory, request
):
    instance = factory()

    if (instance._meta.model_name, field_name) in INVALID_IMAGE_COMBINATIONS:
        request.applymarker(pytest.mark.xfail(run=False))

    instance.refresh_from_db()

    file_field = getattr(instance, field_name)
    file_field.save(
        f"{field_name}.jpg",
        create_uploaded_image(width=10, height=20, name=f"{field_name}.jpg"),
    )

    instance.refresh_from_db()

    assert getattr(instance, field_name).url.startswith(
        "http://localhost:9000/grand-challenge-public/"
    )
    assert getattr(instance, f"{field_name}_width") == 10
    assert getattr(instance, f"{field_name}_height") == 20


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field_name", ("logo", "social_image", "banner", "mugshot")
)
@pytest.mark.parametrize(
    "factory",
    (
        AlgorithmFactory,
        ArchiveFactory,
        PostFactory,
        ChallengeFactory,
        OrganizationFactory,
        lambda: UserFactory().user_profile,
        ReaderStudyFactory,
        WorkstationFactory,
    ),
)
def test_height_width_removed_on_deletion(
    uploaded_image, field_name, factory, request
):
    instance = factory()

    if (instance._meta.model_name, field_name) in INVALID_IMAGE_COMBINATIONS:
        request.applymarker(pytest.mark.xfail(run=False))

    file_field = getattr(instance, field_name)

    file_field.save(
        f"{field_name}.jpg",
        create_uploaded_image(width=10, height=20, name=f"{field_name}.jpg"),
    )
    file_field.delete()

    instance.refresh_from_db()

    assert not getattr(instance, field_name)
    assert getattr(instance, f"{field_name}_width") is None
    assert getattr(instance, f"{field_name}_height") is None
