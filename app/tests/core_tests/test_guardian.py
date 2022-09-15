import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.views.generic import ListView
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
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


@pytest.mark.django_db
def test_permission_list_mixin():
    alg = AlgorithmFactory()
    user = UserFactory()

    request = HttpRequest()
    request.user = user

    class View(PermissionListMixin, ListView):
        model = Algorithm
        permission_required = "algorithms.view_algorithm"

    # Add global permission, algorithm should not be included
    assign_perm("algorithms.view_algorithm", user)
    view = View()
    view.request = request
    assert view.get_queryset().count() == 0

    # Add object level permission, algorithm should be included
    assign_perm("algorithms.view_algorithm", user, alg)
    view = View()
    view.request = request
    assert view.get_queryset().count() == 1


@pytest.mark.django_db
def test_object_permission_required_mixin():
    alg = AlgorithmFactory()
    user = UserFactory()

    request = HttpRequest()
    request.user = user

    class View(ObjectPermissionRequiredMixin, ListView):
        model = Algorithm
        permission_required = "algorithms.view_algorithm"
        raise_exception = True

        def get_permission_object(self):
            return Algorithm.objects.first()

    # Add global permission, algorithm should not be included
    assign_perm("algorithms.view_algorithm", user)
    view = View()
    view.request = request
    with pytest.raises(PermissionDenied):
        view.check_permissions(request)

    # Add object level permission, algorithm should be included
    assign_perm("algorithms.view_algorithm", user, alg)
    view = View()
    view.request = request
    view.check_permissions(request)
