from django.conf import settings


class AWSBatchExecutor:
    def __init__(
        self,
        *,
        job_id,
        job_class,
        input_civs,
        input_prefixes,
        output_interfaces,
        exec_image,
        exec_image_sha256,
        memory_limit,
    ):
        self._job_id = job_id
        self._job_label = f"{job_class._meta.app_label}-{job_class._meta.model_name}-{job_id}"
        self._exec_image = exec_image
        self._exec_image_sha256 = exec_image_sha256
        self._input_civs = input_civs
        self._input_prefixes = input_prefixes
        self._output_interfaces = output_interfaces
        self._memory_limit = min(
            memory_limit, settings.COMPONENTS_MEMORY_LIMIT
        )

        self._stdout = ""
        self._stderr = ""
        self._outputs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def provision(self):
        raise NotImplementedError

    def execute(self):
        raise NotImplementedError

    def await_completion(self):
        raise NotImplementedError

    def get_outputs(self):
        raise NotImplementedError

    def deprovision(self):
        raise NotImplementedError

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def duration(self):
        raise NotImplementedError

    @property
    def outputs(self):
        return self._outputs
