import pytest

from tests.factories import ChallengeFactory
from tests.incentives_tests.factories import IncentiveFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_incentive_serialization(client):
    challenge = ChallengeFactory(hidden=False)
    i1, i2, _ = IncentiveFactory.create_batch(3)

    challenge.incentives.set([i1, i2])

    response = get_view_for_user(
        client=client,
        viewname="api:challenge-detail",
        reverse_kwargs={"slug": challenge.short_name},
    )

    assert response.status_code == 200
    assert response.json()["incentives"] == [i1.incentive, i2.incentive]
