import re
from uuid import uuid4

import pytest

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.components.backends.utils import get_sagemaker_model_name
from grandchallenge.evaluation.models import Method


@pytest.mark.parametrize("model", [Method, AlgorithmImage])
def test_get_sagemaker_model_name(settings, model):
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

    model_name = get_sagemaker_model_name(repo_tag=image.shimmed_repo_tag)

    # Model name must be less than 64 chars and match the given regex
    assert len(model_name) <= 63
    pattern = re.compile(r"^[a-zA-Z0-9]([\-a-zA-Z0-9]*[a-zA-Z0-9])?$")
    assert pattern.match(model_name)
