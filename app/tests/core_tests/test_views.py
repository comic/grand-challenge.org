import json

import pytest
from django.http import HttpRequest
from django.views.generic import ListView
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.guardian import PermissionListMixin
from grandchallenge.datatables.views import PaginatedTableListView
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory


@pytest.mark.django_db
def test_main(client):
    url = reverse("home")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_sitemap(client):
    url = reverse("django.contrib.sitemaps.views.sitemap")
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_paginated_table_list_view():
    view = PaginatedTableListView()
    request = HttpRequest()
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    request.GET["length"] = 50
    request.GET["draw"] = 1
    view.model = Algorithm
    view.order_by = "created"
    view.request = request
    resp = view.get(request)

    assert json.loads(resp.content) == {
        "draw": 1,
        "recordsTotal": 0,
        "recordsFiltered": 0,
        "data": [],
        "showColumns": [],
    }


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
