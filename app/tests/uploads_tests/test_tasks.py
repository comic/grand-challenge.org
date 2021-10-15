from datetime import timedelta

import pytest
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.tasks import delete_old_user_uploads
from tests.uploads_tests.factories import UserUploadFactory


@pytest.mark.django_db
def test_uploads_removed():
    statuses = [*UserUpload.StatusChoices.choices]

    old_uploads = UserUploadFactory.create_batch(len(statuses))
    new_upload = UserUploadFactory()

    for ii, upload in enumerate(old_uploads):
        upload.status = statuses[ii][0]
        upload.created -= timedelta(days=5)
        upload.save()

    delete_old_user_uploads()

    for old_upload in old_uploads:
        with pytest.raises(ObjectDoesNotExist):
            old_upload.refresh_from_db()

    new_upload.refresh_from_db()
