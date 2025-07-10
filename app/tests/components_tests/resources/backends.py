import io
import json
import logging

from django.conf import settings
from django.utils.timezone import now

from grandchallenge.components.backends.base import Executor

logger = logging.getLogger(__name__)


class IOCopyExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__start_time = now()

    def execute(self):
        try:
            with io.BytesIO() as f:
                self._s3_client.download_fileobj(
                    Fileobj=f,
                    Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                    Key=self._invocation_key,
                )
                f.seek(0)
                invocation_json = json.loads(f.read().decode("utf-8"))

            for task in invocation_json:
                # Copy inputs to outputs
                for inpt in task["inputs"]:
                    copy_source = {
                        "Bucket": inpt["bucket_name"],
                        "Key": inpt["bucket_key"],
                    }
                    output_key = (
                        f'{task["output_prefix"]}/{inpt["relative_path"]}'
                    )

                    logger.info(f"Copying {copy_source} to {output_key}")

                    self._s3_client.copy(
                        CopySource={
                            "Bucket": inpt["bucket_name"],
                            "Key": inpt["bucket_key"],
                        },
                        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        Key=output_key,
                    )

                # Create results and metrics json files
                for output_filename in ["results", "metrics"]:
                    with io.BytesIO() as f:
                        f.write(
                            json.dumps(
                                {
                                    "score": 1,
                                    "acc": 0.5,
                                    "invocation_json": invocation_json,
                                }
                            ).encode("utf-8")
                        )
                        f.seek(0)
                        self._s3_client.upload_fileobj(
                            Fileobj=f,
                            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                            Key=f'{task["output_prefix"]}/{output_filename}.json',
                        )

                # write arbitrary text file; should not be processed
                with io.BytesIO() as f:
                    f.write(b"Some arbitrary text")
                    f.seek(0)
                    self._s3_client.upload_fileobj(
                        Fileobj=f,
                        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        Key=f'{task["output_prefix"]}/some_text.txt',
                    )

            # Create a task return code
            with io.BytesIO() as f:
                f.write(
                    json.dumps({"pk": self._job_id, "return_code": 0}).encode(
                        "utf-8"
                    )
                )
                f.seek(0)
                self._s3_client.upload_fileobj(
                    Fileobj=f,
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=self._result_key,
                )
        finally:
            self._set_task_logs()

        self._handle_completed_job()

    def handle_event(self, *, event):
        raise RuntimeError("This backend is not event-driven")

    @staticmethod
    def get_job_name(*, event):
        raise NotImplementedError

    @staticmethod
    def get_job_params(*, job_name):
        raise NotImplementedError

    @property
    def duration(self):
        return now() - self.__start_time

    @property
    def usd_cents_per_hour(self):
        return 100

    @property
    def runtime_metrics(self):
        logger.warning("Runtime metrics are not implemented for this backend")
        return

    @property
    def warm_pool_retained_billable_time_in_seconds(self):
        raise NotImplementedError

    def _set_task_logs(self):
        stdout = ["Greetings from stdout"]
        stderr = [
            "UserWarning: Could not google: [Errno ",
            'warn("Hello from stderr")',
        ]

        self._stdout = stdout
        self._stderr = stderr
