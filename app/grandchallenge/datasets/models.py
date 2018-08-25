# -*- coding: utf-8 -*-
import uuid
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core import files
from django.db import models
from django.utils import timezone

from grandchallenge.cases.models import (
    Image,
    RawImageUploadSession,
    RawImageFile,
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.container_exec.backends.docker import (
    Executor,
    put_file,
    cleanup,
)
from grandchallenge.container_exec.exceptions import InputError
from grandchallenge.container_exec.models import ContainerExecJobModel
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.evaluation.models import Submission
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile


class ImageSet(UUIDModel):
    TRAINING = "TRN"
    TESTING = "TST"

    PHASE_CHOICES = ((TRAINING, "Training"), (TESTING, "Testing"))

    challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE)
    phase = models.CharField(
        max_length=3, default=TRAINING, choices=PHASE_CHOICES
    )
    images = models.ManyToManyField(to=Image, related_name="imagesets")

    @property
    def image_index(self):
        return {i.sorter_key: i for i in self.images.all()}

    @property
    def images_with_keys(self):
        return [
            {"key": key, "image": self.image_index[key]}
            for key in sorted(self.image_index)
        ]

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.full_clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "datasets:imageset-detail",
            kwargs={
                "challenge_short_name": self.challenge.short_name,
                "pk": self.pk,
            },
        )

    class Meta:
        unique_together = ("challenge", "phase")


class AnnotationSet(UUIDModel):
    PREDICTION = "P"
    GROUNDTRUTH = "G"

    KIND_CHOICES = ((PREDICTION, "Prediction"), (GROUNDTRUTH, "Ground Truth"))

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    kind = models.CharField(
        max_length=1, default=GROUNDTRUTH, choices=KIND_CHOICES
    )
    images = models.ManyToManyField(to=Image, related_name="annotationsets")
    submission = models.OneToOneField(
        to=Submission, null=True, on_delete=models.SET_NULL, editable=False
    )

    def __str__(self):
        return (
            f"{self.get_kind_display()} annotation set, "
            f"{len(self.images.all())} images, "
            f"created by {self.creator}"
        )

    @property
    def annotation_index(self):
        return {i.sorter_key: i for i in self.images.all()}

    @property
    def missing_annotations(self):
        base_index = self.base.image_index
        annotation_index = self.annotation_index

        missing = base_index.keys() - annotation_index.keys()

        return [
            {"key": key, "base": base_index[key]} for key in sorted(missing)
        ]

    @property
    def extra_annotations(self):
        base_index = self.base.image_index
        annotation_index = self.annotation_index

        extra = annotation_index.keys() - base_index.keys()

        return [
            {"key": key, "annotation": annotation_index[key]}
            for key in sorted(extra)
        ]

    @property
    def matched_images(self):
        base_index = self.base.image_index
        annotation_index = self.annotation_index

        matches = base_index.keys() & annotation_index.keys()

        return [
            {
                "key": key,
                "base": base_index[key],
                "annotation": annotation_index[key],
            }
            for key in sorted(matches)
        ]

    def get_absolute_url(self):
        return reverse(
            "datasets:annotationset-detail",
            kwargs={
                "challenge_short_name": self.base.challenge.short_name,
                "pk": self.pk,
            },
        )


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

            new_uuid = uuid.uuid4()

            start = 0
            for chunk in tarstrm:
                staged_file = StagedFile(
                    csrf="staging_conversion_csrf",
                    client_id=self._job_id,
                    client_filename=info["name"],
                    file_id=new_uuid,
                    timeout=timezone.now() + timedelta(minutes=120),
                    start_byte=start,
                    end_byte=len(chunk) - 1,
                    total_size=info["size"],
                )
                string_file = BytesIO(chunk)
                django_file = files.File(string_file)
                staged_file.file.save(
                    f"{info['name']}_{uuid.uuid4()}", django_file
                )
                staged_file.save()
                assert staged_file.file.size == len(chunk) - start
                start = len(chunk)

            staged_file = StagedAjaxFile(new_uuid)

            images.append(
                RawImageFile(
                    upload_session=upload_session,
                    filename=staged_file.name,
                    staged_file_id=staged_file.uuid,
                )
            )

        upload_session.save()
        RawImageFile.objects.bulk_create(images)


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
