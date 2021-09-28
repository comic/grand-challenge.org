import json

import pytest
from django.http import HttpRequest

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.datatables.views import PaginatedTableListView
from grandchallenge.subdomains.utils import reverse


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
