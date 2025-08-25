from django.db import transaction
from django.db.transaction import on_commit

from grandchallenge.components.tasks import lock_model_instance
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task
@transaction.atomic
def import_dicom_to_healthimaging(*, dicom_import_job_pk):
    job = lock_model_instance(
        app_label="healthimaging",
        model_name="DicomImportJob",
        pk=dicom_import_job_pk,
    )

    # the status to check here will ultimately have to be job.DEIDENTIFIED
    if not job.status == job.PENDING:
        raise RuntimeError(
            "Job is not ready for importing into HealthImaging."
        )

    job.status = job.STARTED
    job.save()

    on_commit(job.import_images)
