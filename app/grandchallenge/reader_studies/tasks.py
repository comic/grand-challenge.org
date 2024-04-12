from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.core.utils.error_messages import (
    format_validation_error_message,
)
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    ReaderStudy,
)


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
        ).get()
        add_score(instance, ground_truth.answer)


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
                upload_session.error_message = format_validation_error_message(
                    error=e
                )
                upload_session.save()
            else:
                civ.save()
                if DisplaySet.objects.filter(
                    reader_study=reader_study, values=civ
                ).exists():
                    continue
                ds = DisplaySet.objects.create(reader_study=reader_study)
                ds.values.add(civ)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
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
            upload_session.error_message = format_validation_error_message(
                error=e
            )
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
