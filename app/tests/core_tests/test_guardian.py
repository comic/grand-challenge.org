from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.views.generic import ListView
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
    get_objects_for_group,
    get_objects_for_user,
)
from grandchallenge.evaluation.models import Evaluation
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.evaluation_tests.factories import EvaluationFactory
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


@pytest.mark.django_db
def test_filter_by_permission():
    user = UserFactory()
    queryset = Evaluation.objects.all()
    evaluation = EvaluationFactory()

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 0

    assign_perm("view_evaluation", user, evaluation)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has user permission
    assert filtered_queryset.count() == 1

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm("view_evaluation", group, evaluation)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has both user and group permission
    assert filtered_queryset.count() == 1

    remove_perm("view_evaluation", user, evaluation)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has group permission
    assert filtered_queryset.count() == 1

    remove_perm("view_evaluation", group, evaluation)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has no permission again
    assert filtered_queryset.count() == 0

    assign_perm("view_evaluation", group, evaluation)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has group permission again
    assert filtered_queryset.count() == 1

    group.user_set.remove(user)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Has no permission again
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_by_permission_joined():
    user = UserFactory()
    queryset = Evaluation.objects.all()
    evaluation1, evaluation2 = EvaluationFactory(), EvaluationFactory()
    group = GroupFactory()
    group.user_set.add(user)

    assign_perm("view_evaluation", group, evaluation1)
    assign_perm("view_evaluation", user, evaluation2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # User has permission to view both
    assert filtered_queryset.count() == 2
    assert {e.pk for e in filtered_queryset} == {
        evaluation1.pk,
        evaluation2.pk,
    }


@pytest.mark.django_db
def test_filter_by_global_permission():
    user = UserFactory()
    queryset = Evaluation.objects.all()
    _ = EvaluationFactory()

    assign_perm("evaluation.view_evaluation", user)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # User global permissions shouldn't count
    assert filtered_queryset.count() == 0

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm("evaluation.view_evaluation", group)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Group global permissions shouldn't count
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_with_superuser():
    user = UserFactory(is_superuser=True)
    queryset = Evaluation.objects.all()
    _ = EvaluationFactory()

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # Superusers see everything
    assert filtered_queryset.count() == 1


@pytest.mark.django_db
def test_works_with_anonymous_user():
    anon = get_anonymous_user()
    queryset = Evaluation.objects.all()
    evaluation = EvaluationFactory()

    assign_perm("view_evaluation", anon, evaluation)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=anon, codename="view_evaluation"
    )
    assert filtered_queryset.count() == 1

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=AnonymousUser(), codename="view_evaluation"
    )
    assert filtered_queryset.count() == 1


@pytest.mark.django_db
def test_filter_ordering():
    user = UserFactory()
    queryset = Evaluation.objects.all().order_by("created")
    evaluation1 = EvaluationFactory()
    evaluation2 = EvaluationFactory()

    evaluation1.created -= timedelta(minutes=10)
    evaluation1.save()

    group = GroupFactory()
    group.user_set.add(user)

    assign_perm("view_evaluation", group, evaluation1)
    assign_perm("view_evaluation", user, evaluation2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        evaluation1.pk,
        evaluation2.pk,
    ]

    remove_perm("view_evaluation", group, evaluation1)
    remove_perm("view_evaluation", user, evaluation2)

    assign_perm("view_evaluation", group, evaluation2)
    assign_perm("view_evaluation", user, evaluation1)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename="view_evaluation"
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        evaluation1.pk,
        evaluation2.pk,
    ]
