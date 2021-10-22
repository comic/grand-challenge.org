import factory
from requests import put

from grandchallenge.uploads.models import UserUpload
from tests.factories import UserFactory


def create_upload_from_file(*, file_path, creator):
    with open(file_path, "rb") as f:
        upload = UserUploadFactory(creator=creator, filename=file_path.name)
        presigned_url = upload.generate_presigned_url(part_number=1)
        response = put(presigned_url, data=f.read())
        upload.complete_multipart_upload(
            parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
        )
        upload.save()

    return upload


class UserUploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserUpload

    creator = factory.SubFactory(UserFactory)
