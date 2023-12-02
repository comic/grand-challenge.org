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


@pytest.mark.django_db
def test_filter_by_permission():
    user = UserFactory()
    queryset = Algorithm.objects.all()
    algorithm = AlgorithmFactory()
    codename = "view_algorithm"

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 0

    assign_perm(codename, user, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has user permission
    assert filtered_queryset.count() == 1

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has both user and group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, user, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has no permission again
    assert filtered_queryset.count() == 0

    assign_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has group permission again
    assert filtered_queryset.count() == 1

    group.user_set.remove(user)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has no permission again
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_by_permission_no_user():
    user = UserFactory()
    queryset = Algorithm.objects.all()
    algorithm = AlgorithmFactory()
    codename = "view_algorithm"

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 0

    assign_perm(codename, user, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has user permission, but they're not allowed
    assert filtered_queryset.count() == 0

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has both user and group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, user, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has no permission again
    assert filtered_queryset.count() == 0

    assign_perm(codename, group, algorithm)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has group permission again
    assert filtered_queryset.count() == 1

    group.user_set.remove(user)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # Has no permission again
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_by_permission_joined():
    user = UserFactory()
    queryset = Algorithm.objects.all()
    algorithm1, algorithm2 = AlgorithmFactory(), AlgorithmFactory()
    group = GroupFactory()
    group.user_set.add(user)
    codename = "view_algorithm"

    assign_perm(codename, group, algorithm1)
    assign_perm(codename, user, algorithm2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User has permission to view both
    assert filtered_queryset.count() == 2
    assert {e.pk for e in filtered_queryset} == {
        algorithm1.pk,
        algorithm2.pk,
    }

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=False,
    )
    # User has permission to view both, but only group considered
    assert filtered_queryset.count() == 1
    assert {e.pk for e in filtered_queryset} == {
        algorithm1.pk,
    }


@pytest.mark.django_db
@pytest.mark.parametrize("accept_user_perms", (True, False))
def test_filter_by_global_permission(accept_user_perms):
    user = UserFactory()
    queryset = Algorithm.objects.all()
    _ = AlgorithmFactory()
    codename = "view_algorithm"
    perm = f"algorithms.{codename}"

    assign_perm(perm, user)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=accept_user_perms,
    )
    # User global permissions shouldn't count
    assert filtered_queryset.count() == 0

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm(perm, group)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=accept_user_perms,
    )
    # Group global permissions shouldn't count
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("accept_user_perms", (True, False))
def test_filter_with_superuser(accept_user_perms):
    user = UserFactory(is_superuser=True)
    queryset = Algorithm.objects.all()
    _ = AlgorithmFactory()
    codename = "view_algorithm"

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
        accept_user_perms=accept_user_perms,
    )
    # Superusers see everything
    assert filtered_queryset.count() == 1


@pytest.mark.django_db
def test_works_with_anonymous_user():
    anon = get_anonymous_user()
    queryset = Algorithm.objects.all()
    algorithm = AlgorithmFactory()
    codename = "view_algorithm"

    assign_perm(codename, anon, algorithm)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=anon, codename=codename
    )
    assert filtered_queryset.count() == 1

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=AnonymousUser(), codename=codename
    )
    assert filtered_queryset.count() == 1


@pytest.mark.django_db
def test_filter_ordering():
    user = UserFactory()
    queryset = Algorithm.objects.all().order_by("created")
    algorithm1, algorithm2 = AlgorithmFactory.create_batch(2)
    codename = "view_algorithm"

    algorithm1.created -= timedelta(minutes=10)
    algorithm1.save()

    group = GroupFactory()
    group.user_set.add(user)

    assign_perm(codename, group, algorithm1)
    assign_perm(codename, user, algorithm2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User has permission to view both but ordering must be maintained
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        algorithm1.pk,
        algorithm2.pk,
    ]

    remove_perm(codename, group, algorithm1)
    remove_perm(codename, user, algorithm2)

    assign_perm(codename, group, algorithm2)
    assign_perm(codename, user, algorithm1)

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # User has permission to view both but ordering must be maintained
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        algorithm1.pk,
        algorithm2.pk,
    ]
