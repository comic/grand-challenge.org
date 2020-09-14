from machina.apps.forum_conversation.apps import (
    ForumConversationAppConfig as BaseForumConversationAppConfig,
)


class ForumConversationAppConfig(BaseForumConversationAppConfig):
    name = "grandchallenge.forum_conversation"
