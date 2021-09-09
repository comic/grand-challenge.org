from celery import shared_task
from django.db import transaction

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import Answer, ReaderStudy


@transaction.atomic
def add_score(obj, answer):
    obj.calculate_score(answer)
    obj.save()


@transaction.atomic
def add_image(obj, image):
    obj.answer_image = image
    obj.save()
    image.assign_view_perm_to_creator()
    image.update_viewer_groups_permissions()


@shared_task
def add_scores(*, instance_pk, pk_set):
    instance = Answer.objects.get(pk=instance_pk)
    if instance.is_ground_truth:
        for answer in Answer.objects.filter(
            question=instance.question,
            is_ground_truth=False,
            images__in=pk_set,
        ):
            add_score(answer, instance.answer)
    else:
        ground_truth = Answer.objects.filter(
            question=instance.question,
            is_ground_truth=True,
            images__in=pk_set,
        ).first()
        if ground_truth:
            add_score(instance, ground_truth.answer)


@shared_task
def add_images_to_reader_study(*, upload_session_pk, reader_study_pk):
    images = Image.objects.filter(origin_id=upload_session_pk)
    reader_study = ReaderStudy.objects.get(pk=reader_study_pk)

    reader_study.images.add(*images.all())


@shared_task
def add_image_to_answer(*, upload_session_pk, answer_pk):
    image = Image.objects.get(origin_id=upload_session_pk)
    answer = Answer.objects.get(pk=answer_pk)

    if (
        str(answer.answer["upload_session_pk"]).casefold()
        == str(upload_session_pk).casefold()
    ):
        add_image(answer, image)
    else:
        raise ValueError("Upload session for answer does not match")
