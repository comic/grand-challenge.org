from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.views.generic import ListView, TemplateView
from guardian.core import ObjectPermissionChecker
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from grandchallenge.core.guardian import (
    ObjectPermissionCheckerMixin,
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    filter_by_permission,
    get_objects_for_group,
    get_objects_for_user,
)
from grandchallenge.reader_studies.models import Answer
from tests.factories import GroupFactory, UserFactory
from tests.reader_studies_tests.factories import AnswerFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory, method",
    [
        (GroupFactory, get_objects_for_group),
        (UserFactory, get_objects_for_user),
    ],
)
def test_get_objects_shortcuts(factory, method):
    answer = AnswerFactory()
    subject = factory()

    permission = "reader_studies.view_answer"

    # Add global permission, answer should not be included
    assign_perm(permission, subject)
    assert method(subject, permission).count() == 0

    # Add object level permission, answer should be included
    assign_perm(permission, subject, answer)
    assert method(subject, permission).count() == 1


@pytest.mark.django_db
def test_permission_list_mixin():
    answer = AnswerFactory()
    user = UserFactory()

    request = HttpRequest()
    request.user = user

    class View(PermissionListMixin, ListView):
        model = Answer
        permission_required = "reader_studies.view_answer"

    # Add global permission, algorithm should not be included
    assign_perm("reader_studies.view_answer", user)
    view = View()
    view.request = request
    assert view.get_queryset().count() == 0

    # Add object level permission, algorithm should be included
    assign_perm("reader_studies.view_answer", user, answer)
    view = View()
    view.request = request
    assert view.get_queryset().count() == 1


@pytest.mark.django_db
def test_object_permission_required_mixin():
    answer = AnswerFactory()
    user = UserFactory()

    request = HttpRequest()
    request.user = user

    class View(ObjectPermissionRequiredMixin, ListView):
        model = Answer
        permission_required = "reader_studies.view_answer"
        raise_exception = True

        def get_permission_object(self):
            return Answer.objects.first()

    # Add global permission, algorithm should not be included
    assign_perm("reader_studies.view_answer", user)
    view = View()
    view.request = request
    with pytest.raises(PermissionDenied):
        view.check_permissions(request)

    # Add object level permission, algorithm should be included
    assign_perm("reader_studies.view_answer", user, answer)
    view = View()
    view.request = request
    view.check_permissions(request)


@pytest.mark.django_db
def test_object_permission_checker_mixin():
    user = UserFactory()

    request = HttpRequest()
    request.user = user

    class TestView(ObjectPermissionCheckerMixin, TemplateView):
        model = Answer

    view = TestView()
    view.request = request

    # View adds checker to context
    context = view.get_context_data()
    assert "checker" in context
    assert context["checker"] is view.permission_checker
    assert isinstance(view.permission_checker, ObjectPermissionChecker)


@pytest.mark.django_db
def test_filter_by_permission():
    user = UserFactory()
    queryset = Answer.objects.all()
    answer = AnswerFactory()
    codename = "view_answer"

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 0

    assign_perm(codename, user, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has user permission
    assert filtered_queryset.count() == 1

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm(codename, group, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has both user and group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, user, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, group, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # Has no permission again
    assert filtered_queryset.count() == 0

    assign_perm(codename, group, answer)
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
    queryset = Answer.objects.all()
    answer = AnswerFactory()
    codename = "view_answer"

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # User does not have permission to view
    assert filtered_queryset.count() == 0

    assign_perm(codename, user, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has user permission
    assert filtered_queryset.count() == 1

    group = GroupFactory()
    group.user_set.add(user)
    assign_perm(codename, group, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has both user and group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, user, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has group permission
    assert filtered_queryset.count() == 1

    remove_perm(codename, group, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has no permission again
    assert filtered_queryset.count() == 0

    assign_perm(codename, group, answer)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has group permission again
    assert filtered_queryset.count() == 1

    group.user_set.remove(user)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Has no permission again
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_by_permission_joined():
    user = UserFactory()
    queryset = Answer.objects.all()
    answer1, answer2 = AnswerFactory(), AnswerFactory()
    group = GroupFactory()
    group.user_set.add(user)
    codename = "view_answer"

    assign_perm(codename, group, answer1)
    assign_perm(codename, user, answer2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User has permission to view both
    assert filtered_queryset.count() == 2
    assert {e.pk for e in filtered_queryset} == {
        answer1.pk,
        answer2.pk,
    }


@pytest.mark.django_db
def test_filter_by_global_permission():
    user = UserFactory()
    queryset = Answer.objects.all()
    _ = AnswerFactory()
    codename = "view_answer"
    perm = f"reader_studies.{codename}"

    assign_perm(perm, user)
    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
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
    )
    # Group global permissions shouldn't count
    assert filtered_queryset.count() == 0


@pytest.mark.django_db
def test_filter_with_superuser():
    user = UserFactory(is_superuser=True)
    queryset = Answer.objects.all()
    _ = AnswerFactory()
    codename = "view_answer"

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # Superusers see everything
    assert filtered_queryset.count() == 1


@pytest.mark.django_db
def test_works_with_anonymous_user():
    anon = get_anonymous_user()
    queryset = Answer.objects.all()
    answer = AnswerFactory()
    codename = "view_answer"

    assign_perm(codename, anon, answer)

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
    queryset = Answer.objects.all().order_by("created")
    answer1, answer2 = AnswerFactory.create_batch(2)
    codename = "view_answer"

    answer1.created -= timedelta(minutes=10)
    answer1.save()

    group = GroupFactory()
    group.user_set.add(user)

    assign_perm(codename, group, answer1)
    assign_perm(codename, user, answer2)

    filtered_queryset = filter_by_permission(
        queryset=queryset, user=user, codename=codename
    )
    # User has permission to view both but ordering must be maintained
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        answer1.pk,
        answer2.pk,
    ]

    remove_perm(codename, group, answer1)
    remove_perm(codename, user, answer2)

    assign_perm(codename, group, answer2)
    assign_perm(codename, user, answer1)

    filtered_queryset = filter_by_permission(
        queryset=queryset,
        user=user,
        codename=codename,
    )
    # User has permission to view both but ordering must be maintained
    assert filtered_queryset.count() == 2
    assert [e.pk for e in filtered_queryset] == [
        answer1.pk,
        answer2.pk,
    ]
