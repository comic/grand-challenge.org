from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumConversationAppConfig(AppConfig):
    label = "forum_conversation"
    name = "machina.apps.forum_conversation"
    verbose_name = _("Machina: Forum conversations")
