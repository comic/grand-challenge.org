from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_migrate


def init_users_groups(sender, **kwargs):
    from django.contrib.auth.models import Group
    from guardian.management import create_anonymous_user
    from guardian.utils import get_anonymous_user

    try:
        anon = get_anonymous_user()
    except ObjectDoesNotExist:
        create_anonymous_user(sender, **kwargs)
        anon = get_anonymous_user()

    g_reg_anon, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
    )
    anon.groups.add(g_reg_anon)

    g_reg, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    anon.groups.remove(g_reg)


def rename_site(sender, **kwargs):
    from django.contrib.sites.models import Site

    s = Site.objects.get(pk=settings.SITE_ID)

    desired_domain = settings.SESSION_COOKIE_DOMAIN.lstrip(".")

    if s.domain != desired_domain:
        s.domain = desired_domain
        s.name = desired_domain.split(".")[0].replace("-", " ").title()
        s.save()


class CoreConfig(AppConfig):
    name = "grandchallenge.core"

    def ready(self):
        post_migrate.connect(init_users_groups, sender=self)
        post_migrate.connect(rename_site, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.core.signals  # noqa: F401
