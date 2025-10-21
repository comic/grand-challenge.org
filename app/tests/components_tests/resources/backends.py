import hashlib
import hmac
import io
import json
import logging
import re

from django.conf import settings
from django.db.transaction import on_commit
from django.utils.timezone import now

from grandchallenge.components.backends.amazon_sagemaker_base import (
    ModelChoices,
)
from grandchallenge.components.backends.base import Executor, JobParams
from grandchallenge.components.backends.utils import UUID4_REGEX
from grandchallenge.components.tasks import handle_event

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
                    content = json.dumps(
                        {
                            "score": 1,
                            "acc": 0.5,
                            "invocation_json": invocation_json,
                        }
                    ).encode("utf-8")
                    self._s3_client.upload_fileobj(
                        Fileobj=io.BytesIO(content),
                        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        Key=f'{task["output_prefix"]}/{output_filename}.json',
                    )

                # write arbitrary text file; should not be processed
                self._s3_client.upload_fileobj(
                    Fileobj=io.BytesIO(b"Some arbitrary text"),
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=f'{task["output_prefix"]}/some_text.txt',
                )

            # Create a task return code
            result_json = json.dumps(
                {"pk": self._job_id, "return_code": 0}
            ).encode("utf-8")

            signature = hmac.new(
                key=self._signing_key,
                msg=result_json,
                digestmod=hashlib.sha256,
            ).hexdigest()

            self._s3_client.upload_fileobj(
                Fileobj=io.BytesIO(result_json),
                Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                Key=self._result_key,
                ExtraArgs={
                    "Metadata": {"signature_hmac_sha256": signature},
                },
            )
        finally:
            self._set_task_logs()

        self._handle_completed_job()

        on_commit(
            handle_event.signature(
                kwargs={
                    "event": {
                        "_job_id": self._job_id,
                        "_stdout": self._stdout,
                        "_stderr": self._stderr,
                        "__start_time": self.__start_time,
                    },
                    "backend": f"{self.__class__.__module__}.{self.__class__.__qualname__}",
                }
            ).apply_async
        )

    def handle_event(self, *, event):
        self._stdout = event["_stdout"]
        self._stderr = event["_stderr"]
        self.__start_time = event["__start_time"]

    @staticmethod
    def get_job_name(*, event):
        return event["_job_id"]

    @staticmethod
    def get_job_params(*, job_name):
        model_regex = r"|".join(ModelChoices.labels)
        pattern = rf"(?P<job_model>{model_regex})\-(?P<job_pk>{UUID4_REGEX})\-(?P<attempt>\d{{2}})$"

        result = re.match(pattern, job_name)

        if result is None:
            raise ValueError("Invalid job name")
        else:
            job_app_label, job_model_name = result.group("job_model").split(
                "-"
            )
            job_pk = result.group("job_pk")
            attempt = int(result.group("attempt"))
            return JobParams(
                app_label=job_app_label,
                model_name=job_model_name,
                pk=job_pk,
                attempt=attempt,
            )

    @property
    def duration(self):
        return now() - self.__start_time

    @property
    def usd_cents_per_hour(self):
        return 121

    @property
    def runtime_metrics(self):
        logger.warning("Runtime metrics are not implemented for this backend")
        return

    @property
    def external_admin_url(self):
        return ""

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
