from pathlib import Path
from tempfile import TemporaryDirectory

from django.db import models
from django.utils._os import safe_join

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.docker import (
    Executor,
    cleanup,
    get_file,
    put_file,
)
from grandchallenge.components.models import ComponentJob
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.validators import get_file_mimetype
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.datasets.utils import process_csv_file
from grandchallenge.evaluation.models import Submission


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
        return ""

    def _get_result(self):
        """Read all of the images in /output/ & convert to an UploadSession."""
        base_dir = "/output/"

        with cleanup(
            self._client.containers.run(
                image=self._io_image,
                volumes={self._input_volume: {"bind": base_dir, "mode": "ro"}},
                name=f"{self._job_label}-reader",
                detach=True,
                tty=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        ) as reader:
            self._copy_output_files(container=reader, base_dir=Path(base_dir))

        return {}

    def _copy_output_files(self, *, container, base_dir: Path):
        output_files = {
            base_dir / Path(f)
            for f in container.exec_run(f"find {base_dir} -type f")
            .output.decode()
            .splitlines()
        }

        if not output_files:
            raise ValueError("Output directory is empty")

        job = SubmissionToAnnotationSetJob.objects.get(pk=self._job_id)
        annotationset = AnnotationSet.objects.create(
            creator=job.submission.creator,
            base=job.base,
            submission=job.submission,
            kind=AnnotationSet.PREDICTION,
        )

        if self.__was_unzipped:
            with TemporaryDirectory() as tmpdir:
                input_files = set()

                for file in output_files:
                    tmpfile = safe_join(tmpdir, file.relative_to(base_dir))

                    with open(tmpfile, "wb") as outfile:
                        infile = get_file(container=container, src=file)
                        buffer = True
                        while buffer:
                            buffer = infile.read(1024)
                            outfile.write(buffer)

                    input_files.add(Path(tmpfile))

                importer_result = import_images(files=input_files,)

            annotationset.images.add(*importer_result.new_images)

        else:
            if not len(output_files) == 1:
                raise RuntimeError("This submission has too many files.")

            f = get_file(container=container, src=output_files.pop())
            annotationset.labels = process_csv_file(f)
            annotationset.save()


class SubmissionToAnnotationSetJob(UUIDModel, ComponentJob):
    base = models.ForeignKey(to=ImageSet, on_delete=models.CASCADE)
    submission = models.OneToOneField(to=Submission, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.schedule_job()

    @property
    def container(self):
        class FakeContainer:
            ready = True
            image = None
            image_sha256 = None
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
