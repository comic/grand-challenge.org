import pytest

from grandchallenge.core.fixtures import create_uploaded_image
from grandchallenge.core.tasks import schedule_image_update_tasks
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.blogs_tests.factory import PostFactory
from tests.factories import ChallengeFactory, UserFactory, WorkstationFactory
from tests.organizations_tests.factories import OrganizationFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory

FACTORY_IMAGE_FIELD_COMBINATIONS = {
    (AlgorithmFactory, "logo"),
    (AlgorithmFactory, "social_image"),
    (ArchiveFactory, "logo"),
    (ArchiveFactory, "social_image"),
    (PostFactory, "logo"),
    (ChallengeFactory, "logo"),
    (ChallengeFactory, "social_image"),
    (ChallengeFactory, "banner"),
    (OrganizationFactory, "logo"),
    (lambda: UserFactory().user_profile, "mugshot"),
    (ReaderStudyFactory, "logo"),
    (ReaderStudyFactory, "social_image"),
    (WorkstationFactory, "logo"),
}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,field_name", FACTORY_IMAGE_FIELD_COMBINATIONS
)
def test_height_width_set_on_creation(field_name, factory, settings):
    instance = factory()
    instance.refresh_from_db()

    getattr(instance, field_name).save(
        f"{field_name}.jpg",
        create_uploaded_image(width=10, height=20, name=f"{field_name}.jpg"),
    )

    instance.refresh_from_db()

    assert getattr(instance, field_name).url.startswith(
        f"{settings.AWS_S3_ENDPOINT_URL}/grand-challenge-public/"
    )
    assert getattr(instance, f"{field_name}_width") == 10
    assert getattr(instance, f"{field_name}_height") == 20


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,field_name", FACTORY_IMAGE_FIELD_COMBINATIONS
)
def test_height_width_removed_on_deletion(field_name, factory):
    instance = factory()

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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,field_name", FACTORY_IMAGE_FIELD_COMBINATIONS
)
def test_dimensions_set_by_task(
    field_name, factory, django_capture_on_commit_callbacks, settings
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    instance = factory()

    with django_capture_on_commit_callbacks(execute=True):
        schedule_image_update_tasks()

    instance.refresh_from_db()

    getattr(instance, field_name).save(
        f"{field_name}.jpg",
        create_uploaded_image(width=10, height=20, name=f"{field_name}.jpg"),
    )

    instance.refresh_from_db()
    setattr(instance, f"{field_name}_width", None)
    setattr(instance, f"{field_name}_height", None)
    instance.save()

    with django_capture_on_commit_callbacks() as callbacks:
        schedule_image_update_tasks()

    assert len(callbacks) == 1

    for callback in callbacks:
        callback()

    instance.refresh_from_db()
    assert getattr(instance, f"{field_name}_width") == 10
    assert getattr(instance, f"{field_name}_height") == 20

    with django_capture_on_commit_callbacks() as callbacks:
        schedule_image_update_tasks()

    assert len(callbacks) == 0
