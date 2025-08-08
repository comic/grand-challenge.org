from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumAppConfig(AppConfig):
    label = "forum"
    name = "machina.apps.forum"
    verbose_name = _("Machina: Forum")
