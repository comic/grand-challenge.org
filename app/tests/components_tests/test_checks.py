from grandchallenge.components import check_sagemaker_is_used
from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)


def test_check_sagemaker_is_used(settings):
    expected_backend = f"{AmazonSageMakerTrainingExecutor.__module__}.{AmazonSageMakerTrainingExecutor.__name__}"
    settings.COMPONENTS_DEFAULT_BACKEND = "wrong.backend"

    errors = check_sagemaker_is_used(None)

    assert len(errors) == 1
    assert errors[0].id == "grandchallenge.components.E001"
    assert errors[0].msg == f"{expected_backend} is not the default backend."
