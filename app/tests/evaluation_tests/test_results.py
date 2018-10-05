# -*- coding: utf-8 -*-
import pytest

from tests.factories import ChallengeFactory, ResultFactory


@pytest.mark.django_db
def test_public_private_default():
    c = ChallengeFactory()

    r1 = ResultFactory(challenge=c)

    assert r1.published == True

    c.evaluation_config.auto_publish_new_results = False
    c.evaluation_config.save()

    r2 = ResultFactory(challenge=c)

    assert r2.published == False

    # The public/private status should only update on first save
    r1.save()
    assert r1.published == True
