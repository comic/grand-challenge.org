# -*- coding: utf-8 -*-
import pytest

from tests.factories import ChallengeFactory, ResultFactory


@pytest.mark.django_db
def test_public_private_default():
    c = ChallengeFactory()

    r1 = ResultFactory(challenge=c)

    assert r1.public == True

    c.evaluation_config.new_results_are_public = False
    c.evaluation_config.save()

    r2 = ResultFactory(challenge=c)

    assert r2.public == False

    # The public/private status should only update on first save
    r1.save()
    assert r1.public == True
