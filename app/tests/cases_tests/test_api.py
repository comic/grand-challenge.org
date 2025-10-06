import json
import re
from pathlib import Path

import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import (
    PostProcessImageTaskStatusChoices,
    RawImageUploadSession,
)
from grandchallenge.components.models import ComponentInterface
from grandchallenge.serving.models import Download
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.archives_tests.factories import ArchiveFactory, ArchiveItemFactory
from tests.cases_tests.factories import (
    DICOMImageSetFactory,
    PostProcessImageTaskFactory,
    RawImageUploadSessionFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.factories import ImageFactory, UserFactory
from tests.reader_studies_tests.factories import (
    DisplaySetFactory,
    ReaderStudyFactory,
)
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
def test_filter_origin_images_api_view(client):
    alg = AlgorithmFactory()
    user = UserFactory()
    alg.add_editor(user=user)

    alg_job = AlgorithmJobFactory(
        algorithm_image__algorithm=alg, creator=user, time_limit=60
    )

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
def test_filter_reader_study_images_api_view(
    client, django_capture_on_commit_callbacks
):
    rs1, rs2 = ReaderStudyFactory(), ReaderStudyFactory()
    user = UserFactory()
    rs1.add_editor(user)
    rs2.add_editor(user)

    ds1 = DisplaySetFactory(reader_study=rs1)
    ds2 = DisplaySetFactory(reader_study=rs2)

    im1, im2 = ImageFactory(), ImageFactory()
    civ = ComponentInterfaceValueFactory(image=im1)
    with django_capture_on_commit_callbacks(execute=True):
        ds1.values.add(civ)

    civ = ComponentInterfaceValueFactory(image=im2)
    with django_capture_on_commit_callbacks(execute=True):
        ds2.values.add(civ)

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="api:image-list",
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="api:image-list",
        data={"reader_study": str(rs1.pk)},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["pk"] == str(im1.pk)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "obj,factory",
    [("archive", ArchiveFactory)],
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
def test_session_with_user_upload_to_archive(
    client, settings, django_capture_on_commit_callbacks
):
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
    with django_capture_on_commit_callbacks(execute=True):
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

    ArchiveItem.objects.all().delete()
    upload2 = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    # without interface
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={"uploads": [upload2.api_url], "archive": archive.slug},
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 201
    upload_session = response.json()
    assert upload_session["uploads"] == [upload2.api_url]
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


@pytest.mark.django_db
def test_user_upload_to_archive_item_with_new_interface(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_editor(user=user)
    ci = ComponentInterfaceFactory(
        kind=ComponentInterface.Kind.STRING, title="Test"
    )
    civ = ComponentInterfaceValueFactory(interface=ci)
    item = ArchiveItemFactory(archive=archive)
    item.values.add(civ)
    assert item.values.count() == 1

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )

    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "uploads": [upload.api_url],
                "archive_item": item.pk,
                "interface": "generic-overlay",
            },
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 201
    upload_session = response.json()
    assert upload_session["uploads"] == [upload.api_url]
    item.refresh_from_db()
    assert item.values.count() == 2
    assert "generic-overlay" in [
        item.interface.slug for item in item.values.all()
    ]


@pytest.mark.django_db
def test_user_upload_to_archive_item_with_existing_interface(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_editor(user=user)
    ci = ComponentInterface.objects.filter(slug="generic-overlay").get()
    civ = ComponentInterfaceValueFactory(interface=ci)
    item = ArchiveItemFactory(archive=archive)
    item.values.add(civ)
    assert item.values.count() == 1

    # upload another generic-overlay to the same item
    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "uploads": [upload.api_url],
                "archive_item": item.pk,
                "interface": "generic-overlay",
            },
            HTTP_X_FORWARDED_PROTO="https",
        )
    assert response.status_code == 201
    item.refresh_from_db()
    # check that there is only one civ with the generic-overlay interface
    assert item.values.filter(interface__slug="generic-overlay").count() == 1
    # and that the previously added one is no longer associated with the item
    assert civ not in item.values.all()


@pytest.mark.django_db
def test_user_upload_to_archive_item_without_interface(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_editor(user=user)
    ci = ComponentInterface.objects.filter(slug="generic-overlay").get()
    civ = ComponentInterfaceValueFactory(interface=ci)
    item = ArchiveItemFactory(archive=archive)
    item.values.add(civ)
    assert item.values.count() == 1

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={"uploads": [upload.api_url], "archive_item": item.pk},
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 400
    assert (
        "An interface needs to be defined to upload to an archive item."
        in response.json()["non_field_errors"]
    )


@pytest.mark.django_db
def test_user_upload_to_display_set_without_interface(
    client, settings, django_capture_on_commit_callbacks
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    rs = ReaderStudyFactory()
    rs.add_editor(user=user)
    ci = ComponentInterface.objects.filter(slug="generic-overlay").get()
    civ = ComponentInterfaceValueFactory(interface=ci)
    ds = DisplaySetFactory(reader_study=rs)
    ds.values.add(civ)
    assert ds.values.count() == 1

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )
    with django_capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={"uploads": [upload.api_url], "display_set": ds.pk},
            HTTP_X_FORWARDED_PROTO="https",
        )

    assert response.status_code == 400
    assert (
        "An interface needs to be defined to upload to a display set."
        in response.json()["non_field_errors"]
    )


@pytest.mark.django_db
def test_upload_with_too_many_preprocessing(client, settings):
    settings.CASES_MAX_NUM_USER_POST_PROCESSING_TASKS = 1

    user = UserFactory()
    archive = ArchiveFactory()
    archive.add_editor(user=user)
    item = ArchiveItemFactory(archive=archive)

    upload = create_upload_from_file(
        file_path=Path(__file__).parent / "resources" / "image10x10x10.mha",
        creator=user,
    )

    PostProcessImageTaskFactory()  # Active for another user
    task = PostProcessImageTaskFactory(image__origin__creator=user)

    def do_request():
        return get_view_for_user(
            viewname="api:upload-session-list",
            user=user,
            client=client,
            method=client.post,
            content_type="application/json",
            data={
                "uploads": [upload.api_url],
                "archive_item": item.pk,
                "interface": "generic-overlay",
            },
            HTTP_X_FORWARDED_PROTO="https",
        )

    response = do_request()
    assert response.status_code == 400
    assert (
        "You currently have 1 active image post processing tasks. Please wait for them to complete before trying again."
        in response.json()["non_field_errors"]
    )

    task.status = PostProcessImageTaskStatusChoices.COMPLETED
    task.save()

    respose = do_request()
    assert respose.status_code == 201


@pytest.mark.django_db
def test_dicom_404_without_permission(client):
    image = ImageFactory()
    user = UserFactory()

    response = get_view_for_user(
        viewname="api:image-dicom",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No Image matches the given query."}


@pytest.mark.django_db
def test_dicom_404_if_no_image_set(client):
    image = ImageFactory()
    user = UserFactory()
    assign_perm("view_image", user, image)

    response = get_view_for_user(
        viewname="api:image-dicom",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "This image does not have a DICOM Image Set."
    }
    assert not Download.objects.filter(creator=user, image=image).exists()


@pytest.mark.django_db
def test_dicom_signed_urls(client, settings, monkeypatch):
    settings.AWS_HEALTH_IMAGING_DATASTORE_ID = "test-datastore-id"
    settings.AWS_DEFAULT_REGION = "test-region"
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")

    image = ImageFactory(
        dicom_image_set=DICOMImageSetFactory(
            image_set_id="test-image-set-id",
            image_frame_ids=["test-1", "test-2"],
        )
    )
    user = UserFactory()
    assign_perm("view_image", user, image)

    response = get_view_for_user(
        viewname="api:image-dicom",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.status_code == 200

    signed_urls = response.json()

    def verify_aws_headers(headers):
        x_amz_date_pattern = r"^\d{8}T\d{6}Z$"
        auth_pattern = r"^AWS4-HMAC-SHA256 Credential=test-access-key/\d{8}/test-region/medical-imaging/aws4_request, SignedHeaders=host;x-amz-date, Signature=.+$"

        assert headers.keys() == {"Authorization", "X-Amz-Date"}
        assert re.match(x_amz_date_pattern, headers["X-Amz-Date"])
        assert re.match(auth_pattern, headers["Authorization"])

    assert signed_urls.keys() == {
        "get_image_set_metadata",
        "image_set_id",
        "image_frames",
    }
    assert signed_urls["image_set_id"] == "test-image-set-id"
    assert len(signed_urls["image_frames"]) == 2

    for idx, frame_info in enumerate(signed_urls["image_frames"]):
        assert frame_info.keys() == {"image_frame_id", "get_image_frame"}
        assert frame_info["image_frame_id"] == f"test-{idx + 1}"

        frame_request = frame_info["get_image_frame"]

        assert frame_request.keys() == {"data", "headers", "method", "url"}
        verify_aws_headers(frame_request["headers"])
        assert frame_request["data"] == json.dumps(
            {"imageFrameId": f"test-{idx + 1}"}
        )
        assert frame_request["method"] == "POST"
        assert (
            frame_request["url"]
            == "https://runtime-medical-imaging.test-region.amazonaws.com/datastore/test-datastore-id/imageSet/test-image-set-id/getImageFrame"
        )

    metadata_request = signed_urls["get_image_set_metadata"]
    assert metadata_request.keys() == {"data", "headers", "method", "url"}
    verify_aws_headers(metadata_request["headers"])
    assert metadata_request["data"] == '{"versionId": "1"}'
    assert metadata_request["method"] == "POST"
    assert (
        metadata_request["url"]
        == "https://runtime-medical-imaging.test-region.amazonaws.com/datastore/test-datastore-id/imageSet/test-image-set-id/getImageSetMetadata"
    )


@pytest.mark.django_db
def test_dicom_signed_urls_creates_download_object(client):
    image = ImageFactory(
        dicom_image_set=DICOMImageSetFactory(
            image_set_id="test-image-set-id",
            image_frame_ids=["test-1", "test-2"],
        )
    )
    user = UserFactory()
    assign_perm("view_image", user, image)

    response = get_view_for_user(
        viewname="api:image-dicom",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.status_code == 200
    assert Download.objects.filter(creator=user, image=image).exists()


@pytest.mark.django_db
def test_dicom_image_set_serialized(client):
    image = ImageFactory(
        dicom_image_set=DICOMImageSetFactory(
            image_set_id="test-image-set-id",
            image_frame_ids=["test-1", "test-2"],
        )
    )
    user = UserFactory()
    assign_perm("view_image", user, image)

    response = get_view_for_user(
        viewname="api:image-detail",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.json()["dicom_image_set"] == {
        "image_set_id": "test-image-set-id"
    }


@pytest.mark.django_db
def test_no_dicom_image_set_serialized(client):
    image = ImageFactory()
    user = UserFactory()
    assign_perm("view_image", user, image)

    response = get_view_for_user(
        viewname="api:image-detail",
        reverse_kwargs={"pk": image.pk},
        user=user,
        client=client,
    )

    assert response.json()["dicom_image_set"] is None
