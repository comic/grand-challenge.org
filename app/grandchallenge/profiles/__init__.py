from django.core.checks import Error, register


@register(deploy=True)
def check_dummy_provider_is_not_used(app_configs, **kwargs):
    from django.conf import settings

    errors = []

    if (
        "dummy" in settings.SOCIALACCOUNT_PROVIDERS.keys()
        or "allauth.socialaccount.providers.dummy" in settings.INSTALLED_APPS
    ):
        errors.append(
            Error(
                "The dummy social account provider is configured. This provider should only be used for testing purposes and not in production.",
                hint="Remove the dummy provider from SOCIALACCOUNT_PROVIDERS and INSTALLED_APPS in your settings.",
                id="grandchallenge.profiles.E001",
            )
        )

    return errors
