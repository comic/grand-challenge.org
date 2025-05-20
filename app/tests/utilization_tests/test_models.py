from datetime import datetime, timedelta, timezone

import pytest

from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.utilization.models import (
    JobUtilization,
    SessionUtilization,
)
from grandchallenge.workstations.models import Session
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import EvaluationFactory
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

    j.update_utilization(duration=timedelta(minutes=5))

    job_utilizations = JobUtilization.objects.all()
    assert job_utilizations[0].duration == timedelta(minutes=5)
    assert JobUtilization.objects.average_duration() == timedelta(minutes=5)

    _ = AlgorithmJobFactory(time_limit=60)
    assert JobUtilization.objects.average_duration() == timedelta(minutes=5)


@pytest.mark.django_db
def test_average_duration_filtering():
    j1, j2 = AlgorithmJobFactory.create_batch(2, time_limit=60)
    j1.update_utilization(duration=timedelta(minutes=5))
    j2.update_utilization(duration=timedelta(minutes=10))
    assert JobUtilization.objects.average_duration() == timedelta(minutes=7.5)
    assert JobUtilization.objects.filter(
        algorithm_image=j1.algorithm_image
    ).average_duration() == timedelta(minutes=5)
