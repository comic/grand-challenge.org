import json

import pytest
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import (
    HttpRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.urls import Resolver404
from django.utils.module_loading import import_string

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
)
from grandchallenge.core.views import RedirectPath
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.subdomains.middleware import (
    challenge_subdomain_middleware,
    subdomain_middleware,
    subdomain_urlconf_middleware,
)
from grandchallenge.subdomains.utils import reverse
from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.subdomain_tests.test_middleware import SITE_DOMAIN
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
def test_paginated_table_list_view_post():
    view = PaginatedTableListView()
    request = HttpRequest()
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    request.POST["length"] = 50
    request.POST["draw"] = 1
    view.model = Algorithm
    view.request = request
    resp = view.post(request)

    assert json.loads(resp.content) == {
        "draw": 1,
        "recordsTotal": 0,
        "recordsFiltered": 0,
        "data": [],
    }


@pytest.mark.django_db
def test_paginated_table_list_view_ordering():
    view = PaginatedTableListView()

    request = HttpRequest()
    request.META["HTTP_X_REQUESTED_WITH"] = "XMLHttpRequest"
    request.POST["length"] = 50
    request.POST["draw"] = 1

    view.model = Algorithm
    view.row_template = "datatable_row_template.html"

    view.columns = [
        Column(
            title="Created",
            sort_field="created",
        ),
        Column(
            title="Title",
            sort_field="title",
        ),
    ]

    AlgorithmFactory(title="BbbbbB")
    AlgorithmFactory(title="AaaaaA")

    view.request = request

    resp = view.post(request)
    json_resp = json.loads(resp.content)

    assert json_resp["draw"] == 1
    assert json_resp["recordsTotal"] == 2

    # No ordering via AJAX, check defaults
    assert view.default_sort_column == 0
    assert view.default_sort_order == "desc"

    assert "AaaaaA" == json_resp["data"][0][1].strip()
    assert "BbbbbB" in json_resp["data"][1][1].strip()

    # Swap direction
    request.POST["order[0][dir]"] = "asc"
    resp = view.post(request)
    json_resp = json.loads(resp.content)
    # Also swaped rows
    assert "BbbbbB" == json_resp["data"][0][1].strip()
    assert "AaaaaA" == json_resp["data"][1][1].strip()

    # Change order column
    request.POST["order[0][column]"] = "1"
    resp = view.post(request)
    json_resp = json.loads(resp.content)

    # Also changes the rows
    assert "AaaaaA" == json_resp["data"][0][1].strip()
    assert "BbbbbB" == json_resp["data"][1][1].strip()


@pytest.mark.django_db
def test_healthcheck(client, django_assert_num_queries):
    with django_assert_num_queries(3):
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
    "entity_factory,view_name,kwarg_name,kwarg_entity_attribute,post_data",
    [
        (
            AlgorithmFactory,
            "algorithms:permission-request-create",
            "slug",
            "slug",
            None,
        ),
        (
            ArchiveFactory,
            "archives:permission-request-create",
            "slug",
            "slug",
            None,
        ),
        (
            ReaderStudyFactory,
            "reader-studies:permission-request-create",
            "slug",
            "slug",
            None,
        ),
        (
            ChallengeFactory,
            "participants:registration-create",
            "challenge_short_name",
            "short_name",
            {
                "registration_question_answers-TOTAL_FORMS": "0",
                "registration_question_answers-INITIAL_FORMS": "0",
                "registration_question_answers-MIN_NUM_FORMS": "0",
                "registration_question_answers-MAX_NUM_FORMS": "0",
            },
        ),
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
    client,
    entity_factory,
    view_name,
    kwarg_name,
    kwarg_entity_attribute,
    post_data,
    access_request_handling,
    expected_msg,
):

    u = UserFactory()
    t = entity_factory(access_request_handling=access_request_handling)

    response = get_view_for_user(
        client=client,
        viewname=view_name,
        reverse_kwargs={kwarg_name: getattr(t, kwarg_entity_attribute)},
        user=u,
        method=client.post,
        follow=True,
        data=post_data,
    )

    assert expected_msg in response.rendered_content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "urlconf,subdomain",
    (
        ("root", None),
        ("challenge_subdomain", "c"),
        ("rendering_subdomain", "eu-central-1"),
    ),
)
@pytest.mark.parametrize(
    "error_code,included_exception,expected_return",
    (
        (403, PermissionDenied(), HttpResponseForbidden),
        (404, Resolver404(), HttpResponseNotFound),
        (500, None, HttpResponseServerError),
    ),
)
def test_handler_no_db_calls(
    rf,
    django_assert_num_queries,
    urlconf,
    error_code,
    included_exception,
    settings,
    subdomain,
    expected_return,
):
    handler = import_string(
        import_string(f"config.urls.{urlconf}.handler{error_code}")
    )

    settings.ALLOWED_HOSTS = [f".{SITE_DOMAIN}"]
    ChallengeFactory(short_name="c")

    if subdomain is not None:
        host = f"{subdomain}.{SITE_DOMAIN}"
    else:
        host = SITE_DOMAIN

    request = CurrentSiteMiddleware(lambda x: x)(rf.get("/", HTTP_HOST=host))
    request = subdomain_middleware(lambda x: x)(request)
    request = challenge_subdomain_middleware(lambda x: x)(request)
    request = subdomain_urlconf_middleware(lambda x: x)(request)

    connection.queries_log.clear()

    kwargs = {"request": request}

    if included_exception:
        kwargs["exception"] = included_exception

    with django_assert_num_queries(0):
        response = handler(**kwargs)

    assert response.status_code == error_code
    assert isinstance(response, expected_return)
