from django.apps import AppConfig


class BlogsConfig(AppConfig):
    name = "grandchallenge.blogs"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.blogs.signals  # noqa: F401
