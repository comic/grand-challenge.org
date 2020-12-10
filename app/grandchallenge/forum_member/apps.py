from machina.apps.forum_member.apps import (
    ForumMemberAppConfig as BaseForumMemberAppConfig,
)


class ForumMemberAppConfig(BaseForumMemberAppConfig):
    name = "grandchallenge.forum_member"
