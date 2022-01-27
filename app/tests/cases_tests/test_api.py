from pathlib import Path

import pytest
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import RawImageUploadSession
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import (
    create_completed_upload,
    create_upload_from_file,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_session_list(client):
    u1, u2 = UserFactory(), UserFactory()
    RawImageUploadSessionFactory(creator=u1)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        client=client,
        user=u1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:upload-session-list",
        client=client,
        user=u2,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_upload_session_detail(client):
    u1, u2 = UserFactory(), UserFactory()
    us = RawImageUploadSessionFactory(creator=u1)

    response = get_view_for_user(
        viewname="api:upload-session-detail",
        reverse_kwargs={"pk": us.pk},
        client=client,
        user=u1,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:upload-session-detail",
        reverse_kwargs={"pk": us.pk},
        client=client,
        user=u2,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_upload_sessions_create(client, settings):
    user = UserFactory()
    a = ArchiveFactory()
    a.add_uploader(user)
    # without interface
    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            "archive": a.slug,
            "uploads": [create_completed_upload(user=user).api_url],
        },
    )
    assert response.status_code == 201

    upload_session = RawImageUploadSession.objects.get(
        pk=response.data.get("pk")
    )
    assert upload_session.creator == user

    # with interface
    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            "archive": a.slug,
            "interface": "generic-overlay",
            "uploads": [create_completed_upload(user=user).api_url],
        },
    )
    assert response.status_code == 201

    upload_session = RawImageUploadSession.objects.get(
        pk=response.data.get("pk")
    )
    assert upload_session.creator == user


@pytest.mark.django_db
def test_invalid_upload_sessions(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"archive": None},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "archive": ["This field may not be null."],
        "uploads": ["This field is required."],
    }


@pytest.mark.django_db
def test_empty_data_upload_sessions(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"uploads": ["This field is required."]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_active, expected_response", [(False, 401), (True, 201)]
)
def test_upload_session_post_permissions(client, is_active, expected_response):
    user = UserFactory(is_active=is_active)
    ai = AlgorithmImageFactory()
    ai.algorithm.add_user(user)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "algorithm_image": ai.api_url,
            "uploads": [create_completed_upload(user=user).api_url],
        },
        content_type="application/json",
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_filter_images_api_view(client):
    alg = AlgorithmFactory()
    user = UserFactory()
    alg.add_editor(user=user)

    alg_job = AlgorithmJobFactory(algorithm_image__algorithm=alg, creator=user)

    im = ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im)
    alg_job.outputs.add(civ)

    response = get_view_for_user(
        viewname="api:image-list",
        client=client,
        user=user,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert {r["pk"] for r in response.json()["results"]} == {
        str(i.pk) for i in [*[inpt.image for inpt in alg_job.inputs.all()], im]
    }

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="api:image-list",
        data={"origin": str(im.origin.pk)},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(im.pk)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "obj,factory",
    [("archive", ArchiveFactory), ("reader_study", ReaderStudyFactory)],
)
def test_archive_upload_session_create(client, obj, factory):
    u = UserFactory()
    o = factory()

    # Create the upload session
    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=u,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            obj: o.slug,
            "uploads": [create_completed_upload(user=u).api_url],
        },
    )
    errors = response.json()

    assert response.status_code == 400
    assert "does not exist" in errors[obj][0]

    # Assign permissions
    o.add_editor(u)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=u,
        client=client,
        method=client.post,
        content_type="application/json",
        data={
            obj: o.slug,
            "uploads": [create_completed_upload(user=u).api_url],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "Queued"


@pytest.mark.django_db
def test_session_with_user_upload_to_readerstudy(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    rs = ReaderStudyFactory()
    rs.add_editor(user=user)

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )

    # try upload with interface
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "uploads": [upload.api_url],
                "reader_study": rs.slug,
                "interface": "generic-overlay",
            },
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 400
    assert (
        "An interface can only be defined for archive uploads."
        in response.json()["non_field_errors"]
    )

    # try without interface
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={"uploads": [upload.api_url], "reader_study": rs.slug},
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 201
    upload_session = response.json()
    assert upload_session["uploads"] == [upload.api_url]


@pytest.mark.django_db
def test_session_with_user_upload_to_archive(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_editor(user=user)

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    # with interface
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "uploads": [upload.api_url],
                "archive": archive.slug,
                "interface": "generic-overlay",
            },
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 201
    upload_session = response.json()
    assert upload_session["uploads"] == [upload.api_url]
    item = ArchiveItem.objects.get()
    assert item.values.get().interface.slug == "generic-overlay"

    # without interface
    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={"uploads": [upload.api_url], "archive": archive.slug},
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 201
    upload_session = response.json()
    assert upload_session["uploads"] == [upload.api_url]
    item = ArchiveItem.objects.get()
    assert item.values.get().interface.slug == "generic-medical-image"


@pytest.mark.django_db
def test_session_with_user_duplicate_upload(client):
    user = UserFactory()

    upload1 = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    upload2 = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
        data={"uploads": [upload1.api_url, upload2.api_url]},
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert response.status_code == 400
    assert response.json() == {
        "non_field_errors": ["Filenames must be unique"]
    }
