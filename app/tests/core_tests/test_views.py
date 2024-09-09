import json

import pytest
from django.http import HttpRequest

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.core.views import RedirectPath
from grandchallenge.datatables.views import PaginatedTableListView
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.utils import get_view_for_user


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
def test_healthcheck(client, django_assert_num_queries):
    with django_assert_num_queries(7):
        response = client.get("/healthcheck/")

    assert response.content == b""
    assert response.status_code == 200


@pytest.mark.parametrize(
    "path,expected",
    [
        ("", "https://www.new-netloc.com/"),
        ("blogs", "https://www.new-netloc.com/blogs"),
        ("foo/bar/", "https://www.new-netloc.com/foo/bar/"),
    ],
)
def test_redirect_path(rf, path, expected):
    request = rf.get("/parent/")

    response = RedirectPath.as_view(netloc="www.new-netloc.com")(
        request, path=path
    )

    assert response.status_code == 302
    assert response.url == expected

    response = RedirectPath.as_view(
        netloc="www.new-netloc.com", permanent=True
    )(request, path=path)

    assert response.status_code == 301
    assert response.url == expected


@pytest.mark.django_db
def test_product_redirect(client):
    response = get_view_for_user(url="/aiforradiology/", client=client)

    assert response.status_code == 301
    assert response.url == "https://radiology.healthairegister.com/"

    response = get_view_for_user(
        url="/aiforradiology/product/airs-medical-swiftmr", client=client
    )

    assert response.status_code == 301
    assert (
        response.url
        == "https://radiology.healthairegister.com/product/airs-medical-swiftmr"
    )


@pytest.mark.parametrize(
    "entity_factory,namespace",
    [
        (AlgorithmFactory, "algorithms"),
        (ArchiveFactory, "archives"),
        (ReaderStudyFactory, "reader-studies"),
    ],
)
@pytest.mark.parametrize(
    "access_request_handling,expected_msg",
    [
        (
            AccessRequestHandlingOptions.ACCEPT_VERIFIED_USERS,
            "Your request will be automatically accepted if you verify your account",
        ),
        (AccessRequestHandlingOptions.MANUAL_REVIEW, "is awaiting review"),
    ],
)
@pytest.mark.django_db
def test_permission_request_status_msg(
    client, entity_factory, namespace, access_request_handling, expected_msg
):

    u = UserFactory()
    t = entity_factory(access_request_handling=access_request_handling)

    response = get_view_for_user(
        client=client,
        viewname=f"{namespace}:permission-request-create",
        reverse_kwargs={"slug": t.slug},
        user=u,
        method=client.post,
        follow=True,
    )

    assert expected_msg in response.rendered_content
