# -*- coding: utf-8 -*-
import pytest

from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_case_create_view(client, ChallengeSet):
    response = get_view_for_user(
        client=client,
        viewname='cases:create',
        challenge=ChallengeSet.challenge,
    )

    assert response.status_code == 200
