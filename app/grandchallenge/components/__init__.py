from django.core.checks import Error, register


@register(deploy=True)
def check_sagemaker_is_used(app_configs, **kwargs):
    from django.conf import settings

    from grandchallenge.components.backends.amazon_sagemaker_training import (
        AmazonSageMakerTrainingExecutor,
    )

    expected_backend = f"{AmazonSageMakerTrainingExecutor.__module__}.{AmazonSageMakerTrainingExecutor.__name__}"

    errors = []

    if settings.COMPONENTS_DEFAULT_BACKEND != expected_backend:
        errors.append(
            Error(
                f"{expected_backend} is not the default backend. ",
                hint=f"Set COMPONENTS_DEFAULT_BACKEND={expected_backend} in your environment.",
                id="grandchallenge.components.E001",
            )
        )

    return errors
