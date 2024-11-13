import pytest

from tests.factories import ChallengeRequestFactory, UserFactory
from tests.organizations_tests.factories import OrganizationFactory


@pytest.mark.django_db
def test_user_exempt_from_base_costs(settings):
    user = UserFactory()
    request = ChallengeRequestFactory(creator=user)
    organisation = OrganizationFactory()
    organisation.members_group.user_set.add(user)

    assert (
        request.base_cost_euros
        == settings.CHALLENGE_BASE_COST
        + settings.CHALLENGE_MINIMAL_COMPUTE_AND_STORAGE_IN_EURO
    )

    organisation.exempt_from_base_costs = True
    organisation.save()

    del request.base_cost_euros

    assert (
        request.base_cost_euros
        == settings.CHALLENGE_MINIMAL_COMPUTE_AND_STORAGE_IN_EURO
    )
