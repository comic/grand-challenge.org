from datetime import datetime, timedelta, timezone

import pytest

from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.tasks import (
    create_algorithm_jobs_for_evaluation,
)
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.utilization.models import (
    EvaluationUtilization,
    JobUtilization,
    SessionUtilization,
)
from grandchallenge.workstations.models import Session
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import SessionFactory
from tests.reader_studies_tests.factories import (
    QuestionFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_session_utilization_created_after_session():
    session = SessionFactory()

    assert SessionUtilization.objects.count() == 0

    session.stop()

    assert SessionUtilization.objects.count() == 1

    session_utilization = SessionUtilization.objects.first()

    assert session_utilization.session == session


@pytest.mark.django_db
def test_session_utilization_retained_when_session_deleted():
    session = SessionFactory()
    session.stop()
    session_pk = session.pk
    session_utilization = session.session_utilization
    session_utilization_pk = session_utilization.pk

    session.delete()

    assert not Session.objects.filter(pk__in=[session_pk]).exists()
    assert SessionUtilization.objects.filter(
        pk__in=[session_utilization_pk]
    ).exists()

    session_utilization.refresh_from_db()

    assert session_utilization.session is None


@pytest.mark.django_db
def test_session_utilization_retained_when_creator_deleted():
    session = SessionFactory()
    session.stop()
    session_utilization = session.session_utilization
    session_utilization_pk = session_utilization.pk

    session.creator.delete()

    assert SessionUtilization.objects.filter(
        pk__in=[session_utilization_pk]
    ).exists()

    session_utilization.refresh_from_db()

    assert session_utilization.creator is None


@pytest.mark.django_db
def test_session_utilization_duration(mocker):
    fixed_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    session = SessionFactory()
    session.created = fixed_now - timedelta(minutes=5)
    mocker.patch(
        "grandchallenge.workstations.models.now",
        return_value=fixed_now,
    )

    session.stop()

    assert session.session_utilization.duration == timedelta(minutes=5)


@pytest.mark.django_db
def test_session_utilization_reader_studies():
    session = SessionFactory()
    reader_studies = ReaderStudyFactory.create_batch(2)
    session.reader_studies.set(reader_studies)

    session.stop()

    assert session.session_utilization.reader_studies.count() == 2
    assert set(reader_studies) == set(
        session.session_utilization.reader_studies.all()
    )


@pytest.mark.django_db
def test_session_utilization_no_reader_studies():
    session = SessionFactory()
    session.stop()

    assert session.session_utilization.reader_studies.count() == 0


@pytest.mark.django_db
def test_session_utilization_interactive_algorithm():
    session = SessionFactory()
    question = QuestionFactory(
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session.reader_studies.add(question.reader_study)

    session.stop()

    assert session.session_utilization.interactive_algorithms == [
        InteractiveAlgorithmChoices.ULS23_BASELINE.value
    ]


@pytest.mark.django_db
def test_session_utilization_distinct_interactive_algorithms():
    session = SessionFactory()
    questions = QuestionFactory.create_batch(
        2,
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session.reader_studies.add(questions[0].reader_study)
    session.reader_studies.add(questions[1].reader_study)

    session.stop()

    assert session.session_utilization.interactive_algorithms == [
        InteractiveAlgorithmChoices.ULS23_BASELINE.value
    ]


@pytest.mark.django_db
def test_session_utilization_interactive_algorithms_credit_rate():
    session_without_interactive_alg = SessionFactory()
    question = QuestionFactory.create()
    session_without_interactive_alg.reader_studies.add(question.reader_study)
    session_without_interactive_alg.stop()

    assert (
        session_without_interactive_alg.session_utilization.credits_per_hour
        == 500
    )

    session_with_interactive_alg = SessionFactory()
    question = QuestionFactory.create(
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session_with_interactive_alg.reader_studies.add(question.reader_study)
    session_with_interactive_alg.stop()

    assert (
        session_with_interactive_alg.session_utilization.credits_per_hour
        == 1000
    )


@pytest.mark.django_db
def test_duration():
    j = AlgorithmJobFactory(time_limit=60)
    _ = EvaluationFactory(time_limit=60)

    job_utilizations = JobUtilization.objects.all()
    assert job_utilizations[0].duration is None
    assert JobUtilization.objects.average_duration() is None

    j.utilization.duration = timedelta(minutes=5)
    j.utilization.save()

    job_utilizations = JobUtilization.objects.all()
    assert job_utilizations[0].duration == timedelta(minutes=5)
    assert JobUtilization.objects.average_duration() == timedelta(minutes=5)

    _ = AlgorithmJobFactory(time_limit=60)
    assert JobUtilization.objects.average_duration() == timedelta(minutes=5)


@pytest.mark.django_db
def test_average_duration_filtering():
    j1, j2 = AlgorithmJobFactory.create_batch(2, time_limit=60)
    j1.utilization.duration = timedelta(minutes=5)
    j1.utilization.save()
    j2.utilization.duration = timedelta(minutes=10)
    j2.utilization.save()
    assert JobUtilization.objects.average_duration() == timedelta(minutes=7.5)
    assert JobUtilization.objects.filter(
        algorithm_image=j1.algorithm_image
    ).average_duration() == timedelta(minutes=5)


@pytest.mark.django_db
def test_job_utilization_created_on_job_creation():

    assert JobUtilization.objects.count() == 0

    job = AlgorithmJobFactory(time_limit=60)

    assert JobUtilization.objects.count() == 1

    job_utilization = JobUtilization.objects.first()

    assert job_utilization.job == job


@pytest.mark.django_db
def test_evaluation_utilization_created_on_evaluation_creation():

    assert EvaluationUtilization.objects.count() == 0

    evaluation = EvaluationFactory(time_limit=60)

    assert EvaluationUtilization.objects.count() == 1

    evaluation_utilization = EvaluationUtilization.objects.first()

    assert evaluation_utilization.evaluation == evaluation


@pytest.mark.django_db
def test_job_utilization_created_on_job_sets_properties():
    job = AlgorithmJobFactory(time_limit=60)
    job_utilization = job.job_utilization

    assert job_utilization.creator == job.creator
    assert job_utilization.algorithm_image == job.algorithm_image
    assert job_utilization.algorithm == job.algorithm_image.algorithm


@pytest.mark.django_db
def test_job_utilization_created_on_jobs_for_evaluation_sets_properties():
    algorithm_image = AlgorithmImageFactory(
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    interface = AlgorithmInterfaceFactory()
    algorithm_image.algorithm.interfaces.set([interface])

    archive = ArchiveFactory()
    archive_item = ArchiveItemFactory(archive=archive)
    archive_item.values.set(
        [
            ComponentInterfaceValueFactory(interface=ci)
            for ci in interface.inputs.all()
        ]
    )

    phase = PhaseFactory(
        archive=archive,
        submission_kind=SubmissionKindChoices.ALGORITHM,
    )

    evaluation = EvaluationFactory(
        time_limit=60,
        submission__phase=phase,
        submission__algorithm_image=algorithm_image,
        status=Evaluation.EXECUTING_PREREQUISITES,
    )

    create_algorithm_jobs_for_evaluation(
        evaluation_pk=evaluation.pk, first_run=False
    )

    job_utilization = JobUtilization.objects.get()

    assert job_utilization.phase == phase
    assert job_utilization.archive == phase.archive
    assert job_utilization.challenge == phase.challenge
    assert job_utilization.algorithm_image == algorithm_image
    assert job_utilization.algorithm == algorithm_image.algorithm
    assert job_utilization.creator is None


@pytest.mark.django_db
def test_evaluation_utilization_created_on_evaluation_sets_properties():
    algorithm_image = AlgorithmImageFactory()
    evaluation = EvaluationFactory(
        submission__algorithm_image=algorithm_image, time_limit=60
    )
    evaluation_utilization = evaluation.evaluation_utilization

    assert evaluation_utilization.creator == evaluation.submission.creator
    assert evaluation_utilization.phase == evaluation.submission.phase
    assert (
        evaluation_utilization.external_evaluation
        == evaluation.submission.phase.external_evaluation
    )
    assert (
        evaluation_utilization.archive == evaluation.submission.phase.archive
    )
    assert (
        evaluation_utilization.challenge
        == evaluation.submission.phase.challenge
    )
    assert evaluation_utilization.algorithm_image == algorithm_image
    assert evaluation_utilization.algorithm == algorithm_image.algorithm
