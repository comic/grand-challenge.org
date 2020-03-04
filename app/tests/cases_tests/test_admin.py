from pathlib import Path

import pytest

from tests.cases_tests.factories import (
    RawImageFileFactory,
    RawImageUploadSessionFactory,
)
from tests.factories import StagedFileFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_raw_image_file_download(client, settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    admin = UserFactory(is_staff=True)
    user = UserFactory()
    us = RawImageUploadSessionFactory(creator=user)
    path = Path(__file__).parent / "resources" / "dicom" / "1.dcm"

    f = StagedFileFactory(file__from_path=path)

    rif = RawImageFileFactory(upload_session=us, staged_file_id=f.file_id)

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="admin:cases_rawimagefile_download",
        reverse_kwargs={"object_id": rif.pk},
        follow=True,
    )
    assert response.status_code == 200
    assert "not authorized to access this page" in response.rendered_content

    response = get_view_for_user(
        client=client,
        user=admin,
        viewname="admin:cases_rawimagefile_download",
        reverse_kwargs={"object_id": rif.pk},
    )

    assert response.status_code == 403

    admin.is_superuser = True
    admin.save()
    response = get_view_for_user(
        client=client,
        user=admin,
        viewname="admin:cases_rawimagefile_download",
        reverse_kwargs={"object_id": rif.pk},
    )

    assert response.status_code == 200

    with path.open("rb") as dcm:
        assert dcm.read() == response.content
