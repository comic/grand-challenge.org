from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ForumAttachmentsAppConfig(AppConfig):
    label = "forum_attachments"
    name = "machina.apps.forum_conversation.forum_attachments"
    verbose_name = _("Machina: Forum attachments")
