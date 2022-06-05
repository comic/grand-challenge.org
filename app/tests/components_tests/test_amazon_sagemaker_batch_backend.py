import re
from uuid import uuid4

import pytest

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.components.backends.amazon_sagemaker_batch import (
    AmazonSageMakerBatchExecutor,
)
from grandchallenge.evaluation.models import Method


def test_instantiation():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )
    assert executor


@pytest.mark.parametrize("model", [Method, AlgorithmImage])
def test_model_name_generation(settings, model):
    settings.COMPONENTS_REGISTRY_URL = (
        "000000000000.dkr.ecr.regionregion.amazonaws.com"
    )
    settings.COMPONENTS_REGISTRY_PREFIX = "org-proj-env"
    shimmed_version = "99.99.99"
    pk = uuid4()
    image = model(pk=pk, latest_shimmed_version=shimmed_version)

    assert image.shimmed_repo_tag == (
        "000000000000.dkr.ecr.regionregion.amazonaws.com/"
        f"org-proj-env/{model._meta.app_label}/"
        f"{model._meta.model_name}:{pk}-{shimmed_version}"
    )

    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag=image.shimmed_repo_tag,
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    # Model name must be less than 64 chars and match the given regex
    assert len(executor._model_name) <= 63
    pattern = re.compile(r"^[a-zA-Z0-9]([\-a-zA-Z0-9]*[a-zA-Z0-9])?$")
    assert pattern.match(executor._model_name)
