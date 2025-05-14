from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    NoUserPermissionsAllowed,
)
from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class ForumTopicKindChoices(models.TextChoices):
    DEFAULT = "DEFAULT", "Default topic"
    STICKY = "STICKY", "Sticky topic"
    ANNOUNCE = "ANNOUNCE", "Announcement topic"


class Forum(UUIDModel):

    class Meta:
        permissions = (
            (
                "create_forum_topic",
                "Can create a topic in this forum",
            ),
            (
                "create_sticky_and_announcement_topic",
                "Can create sticky and announcement topics in this forum",
            ),
        )

    @property
    def parent_object(self):
        return self.linked_challenge


class ForumTopic(UUIDModel):
    forum = models.ForeignKey(
        Forum,
        related_name="topics",
        null=False,
        on_delete=models.CASCADE,
    )
    creator = models.ForeignKey(
        get_user_model(),
        related_name="created_forum_topics",
        null=True,
        on_delete=models.SET_NULL,
    )

    subject = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="subject", max_length=64)

    TopicKindChoices = ForumTopicKindChoices
    kind = models.CharField(
        max_length=8,
        choices=TopicKindChoices.choices,
        default=TopicKindChoices.DEFAULT,
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Lock a topic to close it and prevent posts from being added to it.",
    )
    last_post_on = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = [
            "-kind",
            "-last_post_on",
        ]
        permissions = (
            (
                "create_topic_post",
                "Create a post for this topic",
            ),
        )
        unique_together = ("slug", "forum")
        constraints = [
            models.CheckConstraint(
                check=models.Q(kind__in=ForumTopicKindChoices.values),
                name="valid_topic_kind",
            )
        ]

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save()

        if adding:
            self.assign_permissions()
            self.last_post_on = self.created

    def assign_permissions(self):
        # challenge admins and participants can see this topic and add posts to it
        assign_perm(
            "discussion_forums.view_topic",
            self.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "discussion_forums.view_topic",
            self.forum.parent_object.participants_group,
            self,
        )
        assign_perm(
            "discussion_forums.create_topic_post",
            self.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "discussion_forums.create_topic_post",
            self.forum.parent_object.participants_group,
            self,
        )
        # only challenge admins can delete this topic
        assign_perm(
            "discussion_forums.delete_topic",
            self.forum.parent_object.admins_group,
            self,
        )

    def get_absolute_url(self):
        return reverse(
            "discussion-forums:topic-detail",
            kwargs={
                "challenge_short_name": self.forum.parent_object.short_name,
                "slug": self.slug,
            },
        )

    @property
    def is_announcement(self):
        return self.kind == ForumTopicKindChoices.ANNOUNCE

    @property
    def is_sticky(self):
        return self.kind == ForumTopicKindChoices.STICKY

    @property
    def last_post(self):
        return self.posts.last()

    @property
    def num_replies(self):
        return self.posts.count() - 1


class ForumPost(UUIDModel):
    topic = models.ForeignKey(
        ForumTopic,
        null=False,
        related_name="posts",
        on_delete=models.CASCADE,
    )
    creator = models.ForeignKey(
        get_user_model(),
        related_name="created_forum_posts",
        null=True,
        on_delete=models.SET_NULL,
    )

    content = models.TextField()

    class Meta:
        ordering = [
            "created",
        ]

    def __str__(self):
        return self.subject

    @property
    def is_alone(self):
        return self.topic.posts.count() == 1

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.topic.last_post_on = self.created
        self.topic.save()

    def delete(self, *args, **kwargs):
        if self.is_alone:
            self.topic.delete()
        else:
            super().delete(*args, **kwargs)


class ForumUserObjectPermission(NoUserPermissionsAllowed):
    content_object = models.ForeignKey(Forum, on_delete=models.CASCADE)


class ForumGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Forum, on_delete=models.CASCADE)


class ForumTopicUserObjectPermission(NoUserPermissionsAllowed):
    content_object = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)


class ForumTopicGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)


class ForumPostUserObjectPermission(NoUserPermissionsAllowed):
    content_object = models.ForeignKey(ForumPost, on_delete=models.CASCADE)


class ForumPostGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(ForumPost, on_delete=models.CASCADE)
