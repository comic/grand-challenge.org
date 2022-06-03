from grandchallenge.components.backends.amazon_sagemaker_batch import (
    AmazonSageMakerBatchExecutor,
)


def test_instantiation():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )
    assert executor
