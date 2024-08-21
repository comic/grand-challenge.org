import pytest

from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory


@pytest.mark.django_db
def test_public_private_default():
    p = PhaseFactory()

    r1 = EvaluationFactory(
        submission__phase=p, time_limit=p.evaluation_time_limit
    )

    assert r1.published is True

    p.auto_publish_new_results = False
    p.save()

    r2 = EvaluationFactory(
        submission__phase=p, time_limit=p.evaluation_time_limit
    )

    assert r2.published is False

    # The public/private status should only update on first save
    r1.save()
    assert r1.published is True
