# -*- coding: utf-8 -*-
import tarfile
import uuid
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core import files
from django.db import models
from django.utils import timezone

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.container_exec.backends.docker import (
    Executor,
    put_file,
    cleanup,
)
from grandchallenge.container_exec.exceptions import InputError
from grandchallenge.container_exec.models import ContainerExecJobModel
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.evaluation.models import Submission
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile


class SubmissionConversionExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, results_file=None, **kwargs)

    def _copy_input_files(self, writer):
        for file in self._input_files:
            dest_file = "/tmp/submission-src"
            put_file(container=writer, src=file, dest=dest_file)

            with file.open("rb") as f:
                mimetype = get_file_mimetype(f)

            if mimetype.lower() == "application/zip":
                # Unzip the file in the container rather than in the python
                # process. With resource limits this should provide some
                # protection against zip bombs etc.
                writer.exec_run(f"unzip {dest_file} -d /input/")
            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f"mv {dest_file} /input/submission.csv")

    def _execute_container(self):
        """ We do not need to do any conversion, so skip """
        pass

    def _get_result(self):
        """
        Reads all of the images in /output/ and converts to upload session
        """
        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._input_volume: {"bind": "/output/", "mode": "ro"}
                    },
                    detach=True,
                    tty=True,
                    **self._run_kwargs,
                )
            ) as reader:
                self._copy_output_files(container=reader)
        except Exception as exc:
            raise InputError(str(exc))

        return {}

    def _copy_output_files(self, *, container):
        output_files = (
            container.exec_run("ls /output/").output.decode().splitlines()
        )

        if not output_files:
            raise ValueError("Output directory is empty")

        # TODO: This thing should not interact with the database
        job = SubmissionConversionJob.objects.get(pk=self._job_id)
        annotationset = AnnotationSet.objects.create(
            creator=job.submission.creator,
            base=job.base,
            submission=job.submission,
            kind=AnnotationSet.PREDICTION,
        )

        # Create the upload session but do not save it until we have the files
        upload_session = RawImageUploadSession(annotationset=annotationset)

        images = []

        for file in output_files:
            tarstrm, info = container.get_archive(f"/output/{file}")

            file_obj = BytesIO()
            for ts in tarstrm:
                file_obj.write(ts)

            file_obj.seek(0)
            tar = tarfile.open(mode="r", fileobj=file_obj)
            content = tar.extractfile(file)

            new_uuid = uuid.uuid4()

            staged_file = StagedFile(
                csrf="staging_conversion_csrf",
                client_id=self._job_id,
                client_filename=info["name"],
                file_id=new_uuid,
                timeout=timezone.now() + timedelta(minutes=120),
                start_byte=0,
                end_byte=content.raw.size - 1,
                total_size=content.raw.size,
            )
            django_file = files.File(content)
            staged_file.file.save(
                f"{info['name']}_{uuid.uuid4()}", django_file
            )
            staged_file.save()

            staged_file = StagedAjaxFile(new_uuid)

            images.append(
                RawImageFile(
                    upload_session=upload_session,
                    filename=staged_file.name,
                    staged_file_id=staged_file.uuid,
                )
            )

        upload_session.save(skip_processing=True)
        RawImageFile.objects.bulk_create(images)
        upload_session.process_images()


class SubmissionConversionJob(ContainerExecJobModel):
    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    submission = models.OneToOneField(to=Submission, on_delete=models.CASCADE)

    @property
    def container(self):
        class FakeContainer:
            ready = True
            image = settings.CONTAINER_EXEC_IO_IMAGE
            image_sha256 = settings.CONTAINER_EXEC_IO_SHA256

        return FakeContainer()

    @property
    def input_files(self):
        return [self.submission.file]

    @property
    def executor_cls(self):
        return SubmissionConversionExecutor

    def create_result(self, *, result: dict):
        pass
