from datetime import datetime, timedelta, timezone

import pytest

from grandchallenge.reader_studies.interactive_algorithms import (
    InteractiveAlgorithmChoices,
)
from grandchallenge.utilization.models import SessionCost
from grandchallenge.workstations.models import Session
from tests.factories import SessionFactory
from tests.reader_studies_tests.factories import (
    QuestionFactory,
    ReaderStudyFactory,
)


@pytest.mark.django_db
def test_session_cost_created_after_session():
    session = SessionFactory()

    assert SessionCost.objects.count() == 0

    session.stop()

    assert SessionCost.objects.count() == 1

    session_cost = SessionCost.objects.first()

    assert session_cost.session == session


@pytest.mark.django_db
def test_session_cost_retained_when_session_deleted():
    session = SessionFactory()
    session.stop()
    session_pk = session.pk
    session_cost = session.session_cost
    session_cost_pk = session_cost.pk

    session.delete()

    assert not Session.objects.filter(pk__in=[session_pk]).exists()
    assert SessionCost.objects.filter(pk__in=[session_cost_pk]).exists()

    session_cost.refresh_from_db()

    assert session_cost.session is None


@pytest.mark.django_db
def test_session_cost_retained_when_creator_deleted():
    session = SessionFactory()
    session.stop()
    session_cost = session.session_cost
    session_cost_pk = session_cost.pk

    session.creator.delete()

    assert SessionCost.objects.filter(pk__in=[session_cost_pk]).exists()

    session_cost.refresh_from_db()

    assert session_cost.creator is None


@pytest.mark.django_db
def test_session_cost_duration(mocker):
    fixed_now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    session = SessionFactory()
    session.created = fixed_now - timedelta(minutes=5)
    mocker.patch(
        "grandchallenge.workstations.models.now",
        return_value=fixed_now,
    )

    session.stop()

    assert session.session_cost.duration == timedelta(minutes=5)


@pytest.mark.django_db
def test_session_cost_reader_studies():
    session = SessionFactory()
    reader_studies = ReaderStudyFactory.create_batch(2)
    session.reader_studies.set(reader_studies)

    session.stop()

    assert session.session_cost.reader_studies.count() == 2
    assert set(reader_studies) == set(
        session.session_cost.reader_studies.all()
    )


@pytest.mark.django_db
def test_session_cost_no_reader_studies():
    session = SessionFactory()
    session.stop()

    assert session.session_cost.reader_studies.count() == 0


@pytest.mark.django_db
def test_session_cost_interactive_algorithm():
    session = SessionFactory()
    question = QuestionFactory(
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session.reader_studies.add(question.reader_study)

    session.stop()

    assert session.session_cost.interactive_algorithms == [
        InteractiveAlgorithmChoices.ULS23_BASELINE.value
    ]


@pytest.mark.django_db
def test_session_cost_distinct_interactive_algorithms():
    session = SessionFactory()
    questions = QuestionFactory.create_batch(
        2,
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session.reader_studies.add(questions[0].reader_study)
    session.reader_studies.add(questions[1].reader_study)

    session.stop()

    assert session.session_cost.interactive_algorithms == [
        InteractiveAlgorithmChoices.ULS23_BASELINE.value
    ]


@pytest.mark.django_db
def test_session_cost_interactive_algorithms_credit_rate():
    session_without_interactive_alg = SessionFactory()
    question = QuestionFactory.create()
    session_without_interactive_alg.reader_studies.add(question.reader_study)
    session_without_interactive_alg.stop()

    assert session_without_interactive_alg.session_cost.credits_per_hour == 500

    session_with_interactive_alg = SessionFactory()
    question = QuestionFactory.create(
        interactive_algorithm=InteractiveAlgorithmChoices.ULS23_BASELINE,
    )
    session_with_interactive_alg.reader_studies.add(question.reader_study)
    session_with_interactive_alg.stop()

    assert session_with_interactive_alg.session_cost.credits_per_hour == 1000
