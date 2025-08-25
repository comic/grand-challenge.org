from django.conf import settings

from grandchallenge.healthimaging.models import HealthImagingWrapper


def test_transform_job_name():
    importer = HealthImagingWrapper(job_id="1234")

    assert (
        importer._import_job_name
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-HI-1234"
    )


def test_import_s3_uris():
    importer = HealthImagingWrapper(job_id="1234")

    assert (
        importer._import_input_s3_uri
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-HI-1234"
    )
    assert (
        importer._import_output_s3_uri
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-HI-1234"
    )
