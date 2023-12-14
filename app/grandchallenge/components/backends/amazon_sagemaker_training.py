from grandchallenge.components.backends.amazon_sagemaker_base import (
    AmazonSageMakerBaseExecutor,
)


class AmazonSageMakerTrainingExecutor(AmazonSageMakerBaseExecutor):
    @property
    def _log_group_name(self):
        # Hardcoded by AWS
        return "/aws/sagemaker/TrainingJobs"

    @staticmethod
    def get_job_name(*, event):
        raise NotImplementedError

    def _get_job_status(self, *, event):
        raise NotImplementedError

    def _get_start_time(self, *, event):
        raise NotImplementedError

    def _get_end_time(self, *, event):
        raise NotImplementedError

    def _get_instance_name(self, *, event):
        raise NotImplementedError

    def _create_job_boto(self):
        raise NotImplementedError

    def _stop_job_boto(self):
        raise NotImplementedError

    def _get_invocation_json(self, *args, **kwargs):
        # SageMaker Training Jobs expect a list
        invocation_json = super()._get_invocation_json(*args, **kwargs)

        if not isinstance(invocation_json, dict):
            raise RuntimeError(
                "Expected to receive a single invocation JSON object"
            )

        return [invocation_json]
