from pathlib import Path

import pytest

from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory
from tests.cases_tests.factories import (
    RawImageFileFactory,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.factories import ImageFactory, StagedFileFactory, UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import create_upload_from_file
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
def test_upload_sessions_create(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
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
        data={},
        content_type="application/json",
    )
    assert response.status_code == 201

    response = get_view_for_user(
        viewname="api:upload-session-process-images",
        reverse_kwargs={"pk": response.json()["pk"]},
        user=user,
        client=client,
        method=client.patch,
        data={"archive": None},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"archive": ["This field may not be null."]}


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
    assert response.status_code == 201

    response = get_view_for_user(
        viewname="api:upload-session-process-images",
        reverse_kwargs={"pk": response.json()["pk"]},
        user=user,
        client=client,
        method=client.patch,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "non_field_errors": [
            "One of archive, answer or reader study must be set"
        ]
    }


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
        data={"algorithm_image": ai.api_url},
        content_type="application/json",
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_image_file_list(client):
    u1, u2 = UserFactory(), UserFactory()
    us1 = RawImageUploadSessionFactory(creator=u1)
    RawImageFileFactory(upload_session=us1)

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        client=client,
        user=u1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        client=client,
        user=u2,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_image_file_detail(client):
    u1, u2 = UserFactory(), UserFactory()
    us = RawImageUploadSessionFactory(creator=u1)
    rif = RawImageFileFactory(upload_session=us)

    response = get_view_for_user(
        viewname="api:upload-session-file-detail",
        reverse_kwargs={"pk": rif.pk},
        client=client,
        user=u1,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:upload-session-file-detail",
        reverse_kwargs={"pk": rif.pk},
        client=client,
        user=u2,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_image_file_create(client):
    user = UserFactory()
    ai = AlgorithmImageFactory()
    ai.algorithm.add_user(user)
    upload_session = RawImageUploadSessionFactory(creator=user)

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "upload_session": upload_session.api_url,
            "filename": "dummy.bin",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    image_file = RawImageFile.objects.get(pk=response.data.get("pk"))
    assert image_file.upload_session == upload_session

    upload_session = RawImageUploadSessionFactory()

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "upload_session": upload_session.api_url,
            "filename": "dummy.bin",
        },
        content_type="application/json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_invalid_image_file_post(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={"upload_session": None, "filename": "dummy.bin"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "upload_session": ["This field may not be null."]
    }

    upload_session = RawImageUploadSessionFactory(creator=user)
    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={"upload_session": upload_session.api_url, "filename": None},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"filename": ["This field may not be null."]}


@pytest.mark.django_db
def test_empty_data_image_files(client):
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "filename": ["This field is required."],
        "upload_session": ["This field is required."],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_active, expected_response", [(False, 401), (True, 201)]
)
def test_image_file_post_permissions(client, is_active, expected_response):
    user = UserFactory(is_active=is_active)
    upload_session = RawImageUploadSessionFactory(creator=user)
    response = get_view_for_user(
        viewname="api:upload-session-file-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "upload_session": upload_session.api_url,
            "filename": "dummy.bin",
        },
        content_type="application/json",
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_process_images_api_view(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    us = RawImageUploadSessionFactory(creator=user)

    archive = ArchiveFactory()
    archive.add_uploader(user)

    f = StagedFileFactory(
        file__from_path=Path(__file__).parent
        / "resources"
        / "image10x10x10.mha"
    )

    RawImageFileFactory(upload_session=us, staged_file_id=f.file_id)

    def request_processing():
        return get_view_for_user(
            viewname="api:upload-session-process-images",
            reverse_kwargs={"pk": us.pk},
            user=user,
            client=client,
            method=client.patch,
            data={"archive": archive.slug},
            content_type="application/json",
        )

    # First request should work
    response = request_processing()
    assert response.status_code == 200

    # Jobs should only be run once
    response = request_processing()
    assert response.status_code == 400


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
    )

    upload_session = response.json()

    assert response.status_code == 201

    # Try to process the images
    response = get_view_for_user(
        viewname="api:upload-session-process-images",
        reverse_kwargs={"pk": upload_session["pk"]},
        user=u,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={obj: o.slug},
    )

    errors = response.json()

    assert response.status_code == 400
    assert "does not exist" in errors[obj][0]

    # Assign permissions
    o.add_editor(u)

    response = get_view_for_user(
        viewname="api:upload-session-process-images",
        reverse_kwargs={"pk": upload_session["pk"]},
        user=u,
        client=client,
        method=client.patch,
        content_type="application/json",
        data={obj: o.slug},
    )

    assert response.status_code == 200
    assert response.json() == "Image processing job queued."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "obj,factory",
    (("archive", ArchiveFactory), ("reader_study", ReaderStudyFactory)),
)
def test_session_with_user_upload(client, obj, factory):
    user = UserFactory()
    o = factory()
    o.add_editor(user=user)

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        content_type="application/json",
        data={"uploads": [upload.api_url], obj: o.slug},
        HTTP_X_FORWARDED_PROTO="https",
    )

    assert response.status_code == 201
    upload_session = response.json()

    assert upload_session["uploads"] == [upload.api_url]


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
