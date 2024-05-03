from grandchallenge.components import (
    check_dummy_provider_is_not_used,
    check_sagemaker_is_used,
)
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


def test_check_dummy_provider_is_not_used(settings):
    settings.SOCIALACCOUNT_PROVIDERS = {"dummy": {}}

    errors = check_dummy_provider_is_not_used(None)

    assert len(errors) == 1
    assert errors[0].id == "grandchallenge.components.E002"
    assert (
        errors[0].msg
        == "The dummy social account provider is configured. This provider should only be used for testing purposes and not in production."
    )
