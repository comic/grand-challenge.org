from django.conf import settings
from django.core.files import File


class AWSBatchExecutor:
    def __init__(
        self,
        *,
        job_id: str,
        exec_image_sha256: str,
        exec_image_repo_tag: str,
        exec_image_file: File,
        memory_limit: int = settings.COMPONENTS_MEMORY_LIMIT,
    ):
        self._job_id = job_id
        self._exec_image_sha256 = exec_image_sha256
        self._exec_image_repo_tag = exec_image_repo_tag
        self._exec_image_file = exec_image_file
        self._memory_limit = min(
            memory_limit, settings.COMPONENTS_MEMORY_LIMIT
        )

    def provision(self, *, input_civs, input_prefixes):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def await_completion(self):
        raise NotImplementedError

    def get_outputs(self, *, output_interfaces):
        raise NotImplementedError

    def deprovision(self):
        raise NotImplementedError

    @property
    def stdout(self):
        raise NotImplementedError

    @property
    def stderr(self):
        raise NotImplementedError

    @property
    def duration(self):
        raise NotImplementedError
