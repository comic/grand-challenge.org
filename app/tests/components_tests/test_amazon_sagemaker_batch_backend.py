import pytest

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


@pytest.mark.parametrize(
    "memory_limit,requires_gpu,expected_type",
    (
        (10, True, "ml.g4dn.xlarge"),
        (30, True, "ml.g4dn.2xlarge"),
        (6, False, "ml.m5.large"),
        (10, False, "ml.m5.xlarge"),
        (30, False, "ml.m5.2xlarge"),
    ),
)
def test_instance_type(memory_limit, requires_gpu, expected_type):
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        time_limit=60,
        requires_gpu=requires_gpu,
    )

    assert executor._instance_type == expected_type


def test_instance_type_incompatible():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=1337,
        time_limit=60,
        requires_gpu=False,
    )

    with pytest.raises(ValueError):
        _ = executor._instance_type
