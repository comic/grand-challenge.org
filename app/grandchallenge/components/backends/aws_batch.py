from django.conf import settings


class AWSBatchExecutor:
    def __init__(
        self, *, job_id, exec_image, exec_image_sha256, memory_limit,
    ):
        self._job_id = job_id
        self._exec_image = exec_image
        self._exec_image_sha256 = exec_image_sha256
        self._memory_limit = min(
            memory_limit, settings.COMPONENTS_MEMORY_LIMIT
        )

    def provision(self, *, input_civs, input_prefixes):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def await_completion(self):
        raise NotImplementedError

    def get_outputs(self, *, ouput_interfaces):
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
