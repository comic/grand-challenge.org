import pytest

from tests.factories import EvaluationFactory, PhaseFactory


@pytest.mark.django_db
def test_public_private_default():
    p = PhaseFactory()

    r1 = EvaluationFactory(submission__phase=p)

    assert r1.published is True

    p.auto_publish_new_results = False
    p.save()

    r2 = EvaluationFactory(submission__phase=p)

    assert r2.published is False

    # The public/private status should only update on first save
    r1.save()
    assert r1.published is True
