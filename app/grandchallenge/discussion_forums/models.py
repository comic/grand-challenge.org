import math

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.transaction import on_commit
from django_extensions.db.fields import AutoSlugField
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
from grandchallenge.discussion_forums.tasks import create_forum_notifications
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

    def __str__(self):
        return f"Forum for {self.parent_object}"

    @property
    def parent_object(self):
        return self.linked_challenge

    def get_absolute_url(self):
        return reverse(
            "discussion-forums:topic-list",
            kwargs={"challenge_short_name": self.parent_object.short_name},
        )


class ForumTopic(FieldChangeMixin, UUIDModel):
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
    last_post = models.ForeignKey(
        "discussion_forums.ForumPost",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
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
            ("lock_forumtopic", "Lock a topic"),
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
            on_commit(
                create_forum_notifications.signature(
                    kwargs={
                        "object_pk": self.pk,
                        "app_label": self._meta.app_label,
                        "model_name": self._meta.object_name,
                    }
                ).apply_async
            )

        if self.has_changed("is_locked"):
            self.update_create_post_permission()

    def assign_permissions(self):
        # challenge admins and participants can see this topic and add posts to it
        assign_perm(
            "view_forumtopic",
            self.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "view_forumtopic",
            self.forum.parent_object.participants_group,
            self,
        )
        assign_perm(
            "create_topic_post",
            self.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "create_topic_post",
            self.forum.parent_object.participants_group,
            self,
        )
        # only challenge admins can lock and delete this topic
        assign_perm(
            "lock_forumtopic",
            self.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "delete_forumtopic",
            self.forum.parent_object.admins_group,
            self,
        )

    def update_create_post_permission(self):
        groups = [
            self.forum.parent_object.admins_group,
            self.forum.parent_object.participants_group,
        ]
        for group in groups:
            if self.is_locked:
                remove_perm("create_topic_post", group, self)
            else:
                assign_perm("create_topic_post", group, self)

    def mark_as_read(self, *, user):
        if user == get_anonymous_user() or isinstance(user, AnonymousUser):
            return
        TopicReadRecord.objects.update_or_create(
            user=user,
            topic=self,
        )

    def get_absolute_url(self):
        return reverse(
            "discussion-forums:topic-post-list",
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
    def num_replies(self):
        return self.posts.count() - 1

    @property
    def last_page_num(self):
        from grandchallenge.discussion_forums.views import ForumTopicPostList

        post_count = self.posts.count()
        posts_per_page = ForumTopicPostList.paginate_by
        return math.ceil(post_count / posts_per_page)

    def get_unread_topic_posts_for_user(self, *, user):
        try:
            read_record = self.read_by.get(user=user)
            return self.posts.exclude(created__lt=read_record.modified)
        except ObjectDoesNotExist:
            return self.posts


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

    @property
    def is_alone(self):
        return self.topic.posts.count() == 1

    @property
    def is_last_post(self):
        return self.topic.last_post == self

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()
            self.topic.mark_as_read(user=self.creator)
            if not self.is_alone:
                on_commit(
                    create_forum_notifications.signature(
                        kwargs={
                            "object_pk": self.pk,
                            "app_label": self._meta.app_label,
                            "model_name": self._meta.object_name,
                        }
                    ).apply_async
                )

        self.topic.last_post = self
        self.topic.last_post_on = self.created
        self.topic.save()

    def delete(self, *args, **kwargs):
        update_last_post_on = False
        topic = self.topic

        if self.is_alone:
            self.topic.delete()
        elif self.is_last_post:
            update_last_post_on = True

        super().delete(*args, **kwargs)

        if update_last_post_on:
            new_last_post = (
                ForumPost.objects.filter(topic=topic)
                .order_by("created")
                .last()
            )
            topic.last_post = new_last_post
            topic.last_post_on = new_last_post.created
            topic.save()

    def assign_permissions(self):
        # challenge admins and participants can see this post
        assign_perm(
            "view_forumpost",
            self.topic.forum.parent_object.admins_group,
            self,
        )
        assign_perm(
            "view_forumpost",
            self.topic.forum.parent_object.participants_group,
            self,
        )
        # challenge admins and post creator can delete the post
        assign_perm(
            "delete_forumpost",
            self.creator,
            self,
        )
        assign_perm(
            "delete_forumpost",
            self.topic.forum.parent_object.admins_group,
            self,
        )
        # only the creator can change the post
        assign_perm(
            "change_forumpost",
            self.creator,
            self,
        )

    def get_absolute_url(self):
        from grandchallenge.discussion_forums.views import ForumTopicPostList

        position = self.get_relative_position()
        posts_per_page = ForumTopicPostList.paginate_by

        page_number = (position // posts_per_page) + 1
        if page_number > 1:
            return f"{self.topic.get_absolute_url()}?page={page_number}#post-{self.pk}"
        else:
            return f"{self.topic.get_absolute_url()}#post-{self.pk}"

    def get_relative_position(self):
        post_ids = list(self.topic.posts.values_list("pk", flat=True))
        return post_ids.index(self.pk)


class ForumUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()
    content_object = models.ForeignKey(Forum, on_delete=models.CASCADE)


class ForumGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "view_forum",
            "create_forum_topic",
            "create_sticky_and_announcement_topic",
        }
    )
    content_object = models.ForeignKey(Forum, on_delete=models.CASCADE)


class ForumTopicUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()
    content_object = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)


class ForumTopicGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {
            "view_forumtopic",
            "delete_forumtopic",
            "lock_forumtopic",
            "create_topic_post",
        }
    )
    content_object = models.ForeignKey(ForumTopic, on_delete=models.CASCADE)


class ForumPostUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"change_forumpost", "delete_forumpost"})
    content_object = models.ForeignKey(ForumPost, on_delete=models.CASCADE)


class ForumPostGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_forumpost", "delete_forumpost"})
    content_object = models.ForeignKey(ForumPost, on_delete=models.CASCADE)


class TopicReadRecord(UUIDModel):
    user = models.ForeignKey(
        get_user_model(),
        related_name="read_topics",
        on_delete=models.CASCADE,
    )
    topic = models.ForeignKey(
        ForumTopic,
        related_name="read_by",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = [
            "user",
            "topic",
        ]

    def __str__(self):
        return f"{self.user} ({self.topic})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.user.username == settings.ANONYMOUS_USER_NAME or isinstance(
            self.user, AnonymousUser
        ):
            raise ValidationError(
                "Anonymous users cannot be assigned to TopicReadRecord."
            )
