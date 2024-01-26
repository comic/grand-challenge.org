import pytest

from tests.factories import ChallengeRequestFactory, UserFactory
from tests.organizations_tests.factories import OrganizationFactory


@pytest.mark.django_db
def test_user_exempt_from_base_costs():
    user = UserFactory()
    request = ChallengeRequestFactory(creator=user)
    organisation = OrganizationFactory()
    organisation.members_group.user_set.add(user)

    assert request.budget == {
        "Base cost": 5000,
        "Compute costs for phase 1": 1870,
        "Compute costs for phase 2": 0,
        "Data storage cost for phase 1": 10,
        "Data storage cost for phase 2": 0,
        "Docker storage cost": 410,
        "Total phase 1": 1880,
        "Total phase 2": 0,
        "Total": 7290,
    }

    organisation.exempt_from_base_costs = True
    organisation.save()

    del request.budget
    del request.base_cost_euros

    assert request.budget == {
        "Base cost": 0,
        "Compute costs for phase 1": 1870,
        "Compute costs for phase 2": 0,
        "Data storage cost for phase 1": 10,
        "Data storage cost for phase 2": 0,
        "Docker storage cost": 410,
        "Total phase 1": 1880,
        "Total phase 2": 0,
        "Total": 2290,
    }
