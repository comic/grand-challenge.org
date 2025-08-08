from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumTrackingAppConfig(AppConfig):
    label = "forum_tracking"
    name = "machina.apps.forum_tracking"
    verbose_name = _("Machina: Forum tracking")
