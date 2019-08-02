from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "comic.eyra_users"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comic.eyra_users.signals
