from grandchallenge.profiles import check_dummy_provider_is_not_used


def test_check_dummy_provider_is_not_used(settings):

    errors = check_dummy_provider_is_not_used(None)

    assert len(errors) == 1
    assert errors[0].id == "grandchallenge.profiles.E001"
    assert (
        errors[0].msg
        == "The dummy social account provider is configured. This provider should only be used for testing purposes and not in production."
    )

    settings.SOCIALACCOUNT_PROVIDERS = {"dummy": {}}
    settings.INSTALLED_APPS.remove("allauth.socialaccount.providers.dummy")

    errors = check_dummy_provider_is_not_used(None)

    assert len(errors) == 1
    assert errors[0].id == "grandchallenge.profiles.E001"
    assert (
        errors[0].msg
        == "The dummy social account provider is configured. This provider should only be used for testing purposes and not in production."
    )
