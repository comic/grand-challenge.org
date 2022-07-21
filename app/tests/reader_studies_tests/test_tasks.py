import pytest

from grandchallenge.algorithms.exceptions import ImageImportError
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.notifications.models import Notification
from grandchallenge.reader_studies.tasks import (
    add_image_to_display_set,
    create_display_sets_for_upload_session,
    send_failed_file_copy_notification,
)
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_create_display_sets_for_upload_session():
    rs = ReaderStudyFactory()
    image = ImageFactory()
    ci = ComponentInterface.objects.get(slug="generic-medical-image")

    assert rs.display_sets.count() == 0

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image

    create_display_sets_for_upload_session(
        upload_session_pk=image.origin.pk,
        reader_study_pk=rs.pk,
        interface_pk=ci.pk,
    )

    assert rs.display_sets.count() == 1
    assert rs.display_sets.first().values.first().image == image


@pytest.mark.django_db
def test_add_image_to_display_set(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    ds = DisplaySetFactory()
    us = RawImageUploadSessionFactory()
    ci = ComponentInterfaceFactory(kind="IMG")

    error_message = "Image imports should result in a single image"

    with pytest.raises(ImageImportError):
        add_image_to_display_set(
            upload_session_pk=us.pk,
            display_set_pk=ds.pk,
            interface_pk=ci.pk,
        )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message

    im1, im2 = ImageFactory.create_batch(2, origin=us)

    with pytest.raises(ImageImportError):
        add_image_to_display_set(
            upload_session_pk=us.pk,
            display_set_pk=ds.pk,
            interface_pk=ci.pk,
        )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 0
    us.refresh_from_db()
    assert us.status == RawImageUploadSession.FAILURE
    assert us.error_message == error_message

    im2.delete()

    add_image_to_display_set(
        upload_session_pk=us.pk,
        display_set_pk=ds.pk,
        interface_pk=ci.pk,
    )
    assert ComponentInterfaceValue.objects.filter(interface=ci).count() == 1


@pytest.mark.django_db
def test_send_failed_file_copy_notification(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    upload = UserUploadFactory(creator=user)
    rs = ReaderStudyFactory(title="foo-study")
    ds = DisplaySetFactory(reader_study=rs)
    interface = ComponentInterfaceFactory(title="foo-interface")

    send_failed_file_copy_notification(
        display_set_pk=ds.pk,
        interface_pk=interface.pk,
        user_upload_pk=upload.pk,
        error="validation failed",
    )

    assert Notification.objects.count() == 1
    notification = Notification.objects.get()
    assert (
        notification.print_notification(user=notification.user)
        == f"File for interface foo-interface added to {ds.pk} "
        f"in foo-study failed validation:\nvalidation failed."
    )
