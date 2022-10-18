import pytest
from django.test.client import RequestFactory
from guardian.utils import get_anonymous_user

from grandchallenge.api.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from tests.factories import UserFactory


@pytest.mark.django_db
def test_custom_permission_classes():
    anon_user = get_anonymous_user()
    user = UserFactory()

    request = RequestFactory()
    request.method = "GET"
    perm_class_1 = IsAuthenticated()
    perm_class_2 = IsAuthenticatedOrReadOnly()

    request.user = None
    assert not perm_class_1.has_permission(request=request, view=None)
    assert perm_class_2.has_permission(request=request, view=None)

    request.user = anon_user
    assert not perm_class_1.has_permission(request=request, view=None)
    assert perm_class_2.has_permission(request=request, view=None)

    request.user = user
    assert perm_class_1.has_permission(request=request, view=None)
    assert perm_class_2.has_permission(request=request, view=None)

    request.method = "POST"
    request.user = anon_user
    assert not perm_class_2.has_permission(request=request, view=None)
