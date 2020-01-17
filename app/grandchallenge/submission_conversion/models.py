import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import models
from django.utils import timezone

from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from grandchallenge.container_exec.backends.docker import (
    Executor,
    cleanup,
    get_file,
    put_file,
)
from grandchallenge.container_exec.models import ContainerExecJobModel
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.datasets.utils import process_csv_file
from grandchallenge.evaluation.models import Submission
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile


class SubmissionToAnnotationSetExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, results_file=None, **kwargs)
        self.__was_unzipped = False

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
                writer.exec_run(
                    f"unzip {dest_file} -d /input/ -x '__MACOSX/*'"
                )
                self.__was_unzipped = True
            else:
                # Not a zip file, so must be a csv
                writer.exec_run(f"mv {dest_file} /input/submission.csv")

    def _execute_container(self):
        """We do not need to do any conversion, so skip."""
        pass

    def _get_result(self):
        """Read all of the images in /output/ & convert to an UploadSession."""
        base_dir = "/output/"

        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._input_volume: {"bind": base_dir, "mode": "ro"}
                    },
                    name=f"{self._job_label}-reader",
                    detach=True,
                    tty=True,
                    labels=self._labels,
                    **self._run_kwargs,
                )
            ) as reader:
                self._copy_output_files(
                    container=reader, base_dir=Path(base_dir)
                )
        except Exception as exc:
            raise RuntimeError(str(exc))

        return {}

    def _copy_output_files(self, *, container, base_dir: Path):
        output_files = [
            base_dir / Path(f)
            for f in container.exec_run(f"find {base_dir} -type f")
            .output.decode()
            .splitlines()
        ]

        if not output_files:
            raise ValueError("Output directory is empty")

        # TODO: This thing should not interact with the database
        job = SubmissionToAnnotationSetJob.objects.get(pk=self._job_id)
        annotationset = AnnotationSet.objects.create(
            creator=job.submission.creator,
            base=job.base,
            submission=job.submission,
            kind=AnnotationSet.PREDICTION,
        )

        if self.__was_unzipped:

            # Create the upload session but do not save it until we have the
            # files
            upload_session = RawImageUploadSession(annotationset=annotationset)

            images = []

            for file in output_files:
                new_uuid = uuid.uuid4()

                django_file = File(get_file(container=container, src=file))

                staged_file = StagedFile(
                    user_pk_str="staging_conversion_user_pk",
                    client_id=self._job_id,
                    client_filename=file.name,
                    file_id=new_uuid,
                    timeout=timezone.now() + timedelta(hours=24),
                    start_byte=0,
                    end_byte=django_file.size - 1,
                    total_size=django_file.size,
                )
                staged_file.file.save(f"{uuid.uuid4()}", django_file)
                staged_file.save()

                staged_ajax_file = StagedAjaxFile(new_uuid)

                images.append(
                    RawImageFile(
                        upload_session=upload_session,
                        filename=staged_ajax_file.name,
                        staged_file_id=staged_ajax_file.uuid,
                    )
                )

            upload_session.save()
            RawImageFile.objects.bulk_create(images)
            upload_session.process_images()

        else:
            assert len(output_files) == 1

            f = get_file(container=container, src=output_files[0])
            annotationset.labels = process_csv_file(f)
            annotationset.save()


class SubmissionToAnnotationSetJob(UUIDModel, ContainerExecJobModel):
    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    submission = models.OneToOneField(to=Submission, on_delete=models.CASCADE)

    @property
    def container(self):
        class FakeContainer:
            ready = True
            image = settings.CONTAINER_EXEC_IO_IMAGE
            image_sha256 = settings.CONTAINER_EXEC_IO_SHA256
            requires_gpu = False

        return FakeContainer()

    @property
    def input_files(self):
        return [self.submission.file]

    @property
    def executor_cls(self):
        return SubmissionToAnnotationSetExecutor

    def create_result(self, *, result: dict):
        pass
