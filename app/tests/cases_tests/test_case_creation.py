# -*- coding: utf-8 -*-
import pytest

from grandchallenge.cases.models import Case
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_case_create_view(client, ChallengeSet):
    response = get_view_for_user(
        client=client,
        viewname='cases:create',
        challenge=ChallengeSet.challenge,
        method=client.post,
        data={
            'stage': Case.TRAINING
        },
    )

    assert response.status_code == 302

    response = get_view_for_user(
        client=client,
        url=response.url,
    )

    assert response.status_code == 200
