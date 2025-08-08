from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumPollsAppConfig(AppConfig):
    label = "forum_polls"
    name = "machina.apps.forum_conversation.forum_polls"
    verbose_name = _("Machina: Forum polls")
