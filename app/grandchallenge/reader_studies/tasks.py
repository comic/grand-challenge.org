from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from grandchallenge.algorithms.exceptions import ImageImportError
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    ReaderStudy,
)
from grandchallenge.uploads.models import UserUpload


@transaction.atomic
def add_score(obj, answer):
    obj.calculate_score(answer)
    obj.save(update_fields=["score"])


@transaction.atomic
def add_image(obj, image):
    obj.answer_image = image
    obj.save()
    image.assign_view_perm_to_creator()
    image.update_viewer_groups_permissions()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def add_scores_for_display_set(*, instance_pk, ds_pk):
    instance = Answer.objects.get(pk=instance_pk)
    display_set = DisplaySet.objects.get(pk=ds_pk)
    if instance.is_ground_truth:
        for answer in Answer.objects.filter(
            question=instance.question,
            is_ground_truth=False,
            display_set=display_set,
        ):
            add_score(answer, instance.answer)
    else:
        ground_truth = Answer.objects.filter(
            question=instance.question,
            is_ground_truth=True,
            display_set=display_set,
        ).first()
        if ground_truth:
            add_score(instance, ground_truth.answer)


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"],
    throws=(ImageImportError,),
)
def add_image_to_display_set(
    *, upload_session_pk, display_set_pk, interface_pk
):
    display_set = DisplaySet.objects.get(pk=display_set_pk)
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    try:
        image = Image.objects.get(origin_id=upload_session_pk)
    except (Image.DoesNotExist, Image.MultipleObjectsReturned):
        error_message = "Image imports should result in a single image"
        upload_session.status = RawImageUploadSession.FAILURE
        upload_session.error_message = error_message
        upload_session.save()
        raise ImageImportError(error_message)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    with transaction.atomic():
        display_set.values.remove(
            *display_set.values.filter(interface=interface)
        )
        civ = ComponentInterfaceValue.objects.filter(
            interface=interface, image=image
        ).first()
        if civ is None:
            civ = ComponentInterfaceValue(interface=interface)
        civ.image = image
        try:
            civ.full_clean()
        except ValidationError as e:
            upload_session.status = RawImageUploadSession.FAILURE
            upload_session.error_message = e.message
            upload_session.save()
        else:
            civ.save()
            display_set.values.add(civ)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def add_file_to_display_set(
    *,
    user_upload_pk,
    display_set_pk,
    interface_pk,
    civ_pk=None,
):
    user_upload = UserUpload.objects.get(pk=user_upload_pk)
    display_set = DisplaySet.objects.get(pk=display_set_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    with transaction.atomic():
        if civ_pk is None:
            civ = ComponentInterfaceValue(interface=interface)
        else:
            civ = ComponentInterfaceValue.objects.get(pk=civ_pk)
        user_upload.copy_object(to_field=civ.file)
        try:
            civ.full_clean()
        except ValidationError as e:
            transaction.on_commit(
                send_failed_file_copy_notification.signature(
                    kwargs={
                        "display_set_pk": display_set_pk,
                        "interface_pk": interface_pk,
                        "user_upload_pk": user_upload_pk,
                        "error": str(e),
                    },
                    immutable=True,
                )
            )
        else:
            civ.save()
            display_set.values.add(civ)


@shared_task
def send_failed_file_copy_notification(
    *, display_set_pk, interface_pk, user_upload_pk, error
):
    user_upload = UserUpload.objects.get(pk=user_upload_pk)
    display_set = DisplaySet.objects.get(pk=display_set_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    Notification.send(
        type=NotificationType.NotificationTypeChoices.FILE_COPY_STATUS,
        actor=user_upload.creator,
        message=(
            f"File for interface {interface.title} added to {display_set_pk} "
            f"in {display_set.reader_study.title} failed validation: {error}."
        ),
        target=display_set.reader_study,
        description=display_set.reader_study.get_absolute_url(),
    )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def create_display_sets_for_upload_session(
    *, upload_session_pk, reader_study_pk, interface_pk
):
    images = Image.objects.filter(origin_id=upload_session_pk)
    reader_study = ReaderStudy.objects.get(pk=reader_study_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    with transaction.atomic():
        for image in images:
            civ = ComponentInterfaceValue.objects.filter(
                interface=interface, image=image
            ).first()
            if civ is None:
                civ = ComponentInterfaceValue(interface=interface)
            civ.image = image
            try:
                civ.full_clean()
            except ValidationError as e:
                upload_session.status = RawImageUploadSession.FAILURE
                upload_session.error_message = e.message
                upload_session.save()
            else:
                civ.save()
                if DisplaySet.objects.filter(
                    reader_study=reader_study, values=civ
                ).exists():
                    continue
                ds = DisplaySet.objects.create(reader_study=reader_study)
                ds.values.add(civ)


@shared_task
def add_image_to_answer(*, upload_session_pk, answer_pk):
    image = Image.objects.get(origin_id=upload_session_pk)
    answer = Answer.objects.get(pk=answer_pk)
    question = answer.question

    if (
        str(answer.answer["upload_session_pk"]).casefold()
        == str(upload_session_pk).casefold()
    ):
        try:
            question._validate_voxel_values(image)
        except ValidationError as e:
            upload_session = RawImageUploadSession.objects.get(
                pk=upload_session_pk
            )
            upload_session.status = RawImageUploadSession.FAILURE
            upload_session.error_message = e.message
            upload_session.save()
        else:
            add_image(answer, image)
    else:
        raise ValueError("Upload session for answer does not match")


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def copy_reader_study_display_sets(*, orig_pk, new_pk):
    orig = ReaderStudy.objects.get(pk=orig_pk)
    new = ReaderStudy.objects.get(pk=new_pk)

    with transaction.atomic():
        for ds in orig.display_sets.all():
            new_ds = DisplaySet.objects.create(reader_study=new)
            new_ds.values.set(ds.values.all())
