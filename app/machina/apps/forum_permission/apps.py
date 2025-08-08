from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumPermissionAppConfig(AppConfig):
    label = "forum_permission"
    name = "machina.apps.forum_permission"
    verbose_name = _("Machina: Forum permissions")
