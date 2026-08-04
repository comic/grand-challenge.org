from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from lambda_tasks.decorators import lambda_task

from config.lambda_tasks import (
    LONG_TASK_HARD_TIMEOUT,
    LONG_TASK_SOFT_TIMEOUT,
    LambdaTaskQueueChoices,
)
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


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def answers_from_ground_truth(
    *, reader_study_pk: str | UUID, target_user_pk: int
):
    reader_study = ReaderStudy.objects.get(pk=reader_study_pk)
    target_user = get_user_model().objects.get(pk=target_user_pk)

    all_answers = Answer.objects.filter(question__reader_study=reader_study)

    for answer in (
        all_answers.filter(is_ground_truth=True)
        .prefetch_related("question__options")
        .select_related("question")
    ):
        # Simplify permissions and create new answers
        answer._state.adding = True
        answer.id = None
        answer.pk = None
        answer.is_ground_truth = False
        answer.creator = target_user
        Answer.validate(
            creator=answer.creator,
            question=answer.question,
            answer=answer.answer,
            display_set=answer.display_set,
            is_ground_truth=answer.is_ground_truth,
        )

        answer.save()


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def bulk_assign_scores_for_reader_study(*, reader_study_pk: str | UUID):
    ground_truth = Answer.objects.filter(
        question__reader_study__pk=reader_study_pk,
        is_ground_truth=True,
    ).all()

    def key(answer):
        return (str(answer.question_id), str(answer.display_set_id))

    ground_truth_lookup = {}
    for answer in ground_truth:
        ground_truth_lookup[key(answer)] = answer

    answers = Answer.objects.filter(
        question__reader_study__pk=reader_study_pk,
        is_ground_truth=False,
    ).prefetch_related("question")

    for answer in answers:
        gt_answer = ground_truth_lookup.get(key(answer))
        if gt_answer is not None:
            answer.calculate_score(ground_truth=gt_answer.answer)
        else:
            # Sanity: should already be none, but just to be sure
            answer.score = None

    Answer.objects.bulk_update(answers, ["score"])


@lambda_task
def create_display_sets_for_upload_session(
    *,
    upload_session_pk: str | UUID,
    reader_study_pk: str | UUID,
    interface_pk: int,
):
    images = Image.objects.filter(origin_id=upload_session_pk)
    reader_study = ReaderStudy.objects.get(pk=reader_study_pk)
    interface = ComponentInterface.objects.get(pk=interface_pk)
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_pk)

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


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def add_image_to_answer(
    *, upload_session_pk: str | UUID, answer_pk: str | UUID
):
    image = Image.objects.get(origin_id=upload_session_pk)
    answer = Answer.objects.get(pk=answer_pk)
    question = answer.question

    if (
        answer.answer is not None
        and str(answer.answer["upload_session_pk"]).casefold()
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
            return {"status": "Voxel values for answer are invalid"}
        else:
            answer.answer_image = image
            answer.save()
            image.assign_view_perm_to_creator()
            image.update_viewer_groups_permissions()
            return {"status": "Answer successfully updated"}
    else:
        return {
            "status": f"Upload session for answer ({answer.answer}) does not match {upload_session_pk}"
        }


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G,
    soft_timeout=LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=LONG_TASK_HARD_TIMEOUT,
)
def copy_reader_study_display_sets(*, orig_pk: str | UUID, new_pk: str | UUID):
    orig = ReaderStudy.objects.get(pk=orig_pk)
    new = ReaderStudy.objects.get(pk=new_pk)

    for ds in orig.display_sets.all():
        new_ds = DisplaySet.objects.create(
            reader_study=new,
            order=ds.order,
            title=ds.title,
        )
        new_ds.values.set(ds.values.all())
