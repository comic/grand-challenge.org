from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    name = "grandchallenge.organizations"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.organizations.signals  # noqa: F401
