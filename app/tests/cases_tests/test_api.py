import pytest
from tests.utils import get_view_for_user
from tests.factories import UserFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    ResultFactory,
)
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
def test_upload_session_list(client):
    upload_session_1, upload_session_2 = (
        RawImageUploadSessionFactory(),
        RawImageUploadSessionFactory(),
    )

    user = UserFactory(is_staff=True)
    response = get_view_for_user(
        viewname="api:upload-sessions-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        viewname="api:upload-sessions-detail",
        reverse_kwargs={"pk": upload_session_1.pk},
        user=user,
        client=client,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_sessions_create(client):
    algo = AlgorithmImageFactory()
    result = ResultFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:upload-sessions-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "imageset": None,
            "algorithm": algo.api_url,
            "algorithm_result": result.api_url,
            "annotationset": None,
            "reader_study": None,
        },
        content_type="application/json",
    )
    print(response.json())
    assert response.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_staff, expected_response", [(False, 403), (True, 201)]
)
def test_upload_session_post_permissions(client, is_staff, expected_response):
    user = UserFactory(is_staff=is_staff)
    algo = AlgorithmImageFactory()
    result = ResultFactory()
    rs = ReaderStudyFactory()
    response = get_view_for_user(
        viewname="api:upload-sessions-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "imageset": None,
            "algorithm": algo.api_url,
            "algorithm_result": result.api_url,
            "annotationset": None,
            "reader_study": rs.api_url,
        },
        content_type="application/json",
    )
    assert response.status_code == expected_response
