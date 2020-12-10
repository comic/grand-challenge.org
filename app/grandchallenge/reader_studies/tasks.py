from celery import shared_task
from django.db import transaction

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import Answer, ReaderStudy


@transaction.atomic
def add_score(obj, answer):
    obj.calculate_score(answer)
    obj.save()


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
