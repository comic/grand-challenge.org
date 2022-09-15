import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.core.guardian import (
    get_objects_for_group,
    get_objects_for_user,
)
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import GroupFactory, UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory, method",
    [
        (GroupFactory, get_objects_for_group),
        (UserFactory, get_objects_for_user),
    ],
)
def test_get_objects_shortcuts(factory, method):
    alg = AlgorithmFactory()
    subject = factory()

    # Add global permission, algorithm should not be included
    assign_perm("algorithms.view_algorithm", subject)
    assert method(subject, "algorithms.view_algorithm").count() == 0

    # Add object level permission, algorithm should be included
    assign_perm("algorithms.view_algorithm", subject, alg)
    assert method(subject, "algorithms.view_algorithm").count() == 1
