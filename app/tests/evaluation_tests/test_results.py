import pytest

from tests.factories import ChallengeFactory, JobFactory


@pytest.mark.django_db
def test_public_private_default():
    c = ChallengeFactory()

    r1 = JobFactory(submission__challenge=c)

    assert r1.published is True

    c.evaluation_config.auto_publish_new_results = False
    c.evaluation_config.save()

    r2 = JobFactory(submission__challenge=c)

    assert r2.published is False

    # The public/private status should only update on first save
    r1.save()
    assert r1.published is True
