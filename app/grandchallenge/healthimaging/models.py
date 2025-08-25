import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.uploads.models import UserUpload


class HealthImagingWrapper:
    def __init__(self, *args, job_id: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.__health_imaging_client = None
        self._job_id = job_id

    @property
    def _health_imaging_client(self):
        if self.__health_imaging_client is None:
            self.__health_imaging_client = boto3.client(
                "medical-imaging",
                region_name=settings.AWS_HEALTH_IMAGING_REGION_NAME,
            )
        return self.__health_imaging_client

    @property
    def _import_job_name(self):
        # HealthImaging requires job names to be max 64 chars
        return f"{settings.COMPONENTS_REGISTRY_PREFIX}-HI-{self._job_id}"

    @property
    def _import_input_s3_uri(self):
        return f"s3://{settings.AWS_HEALTH_IMAGING_INPUT_BUCKET_NAME}/{self._job_id}"

    @property
    def _import_output_s3_uri(self):
        return f"s3://{settings.AWS_HEALTH_IMAGING_OUTPUT_BUCKET_NAME}/{self._job_id}"

    def start_dicom_import_job(self):
        """
        Start a HealthImaging DICOM import job.
        """
        job = self._health_imaging_client.start_dicom_import_job(
            jobName=self._import_job_name,
            datastoreId=settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
            dataAccessRoleArn=settings.AWS_HEALTH_IMAGING_IMPORT_ROLE_ARN,
            inputS3Uri=self._import_input_s3_uri,
            outputS3Uri=self._import_output_s3_uri,
        )
        return job["jobId"]


class DicomImportJob(UUIDModel):
    PENDING = 0
    DEIDENTIFYING = 1
    DEIDENTIFIED = 2
    STARTED = 3
    REQUEUED = 4
    FAILURE = 5
    SUCCESS = 6
    CANCELLED = 7

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (DEIDENTIFYING, "De-Identifying"),
        (DEIDENTIFIED, "De-Identified"),
        (STARTED, "Importing"),
        (REQUEUED, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
    )

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    user_uploads = models.ManyToManyField(
        UserUpload, blank=True, related_name="dicom_import_jobs"
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )

    error_message = models.TextField(blank=False, null=True, default=None)

    def get_importer(self):
        return HealthImagingWrapper(job_id=self.pk)

    def import_images(self):
        importer = self.get_importer()
        try:
            importer.start_dicom_import_job()
        except ClientError:
            self.status = DicomImportJob.FAILURE
            self.error_message = "An unexpected error occurred"
            self.save()
            raise
