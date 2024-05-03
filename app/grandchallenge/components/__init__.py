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
                f"{expected_backend} is not the default backend.",
                hint=f"Set COMPONENTS_DEFAULT_BACKEND={expected_backend} in your environment.",
                id="grandchallenge.components.E001",
            )
        )

    return errors


@register(deploy=True)
def check_dummy_provider_is_not_used(app_configs, **kwargs):
    from django.conf import settings

    errors = []

    if "dummy" in settings.SOCIALACCOUNT_PROVIDERS.keys():
        errors.append(
            Error(
                "The dummy social account provider is configured. This provider should only be used for testing purposes and not in production.",
                hint="Remove the dummy provider from SOCIALACCOUNT_PROVIDERS in your settings.",
                id="grandchallenge.components.E002",
            )
        )

    return errors
