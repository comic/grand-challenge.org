from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.fields import AutoSlugField

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class TopicTypeChoices(models.TextChoices):
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


class Topic(UUIDModel):
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
    slug = AutoSlugField(populate_from="subject", max_length=255)

    TopicTypeChoices = TopicTypeChoices
    type = models.CharField(
        max_length=8,
        choices=TopicTypeChoices.choices,
        default=TopicTypeChoices.DEFAULT,
    )

    locked = models.BooleanField(
        default=False,
        help_text="Lock a topic to close it and prevent posts from being added to it.",
    )
    last_post_on = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = [
            "-type",
            "-last_post_on",
        ]
        permissions = (
            (
                "create_topic_post",
                "Create a post for this topic",
            ),
        )

    def __str__(self):
        return self.subject

    def get_absolute_url(self):
        return reverse(
            "discussion-forums:topic-detail",
            kwargs={
                "challenge_short_name": self.forum.linked_challenge.short_name,
                "pk": self.pk,
            },
        )

    @property
    def is_announcement(self):
        return self.type == TopicTypeChoices.ANNOUNCE

    @property
    def is_sticky(self):
        return self.type == TopicTypeChoices.STICKY

    @property
    def last_post(self):
        return self.posts.last()

    @property
    def num_replies(self):
        return self.posts.count() - 1


class Post(UUIDModel):
    topic = models.ForeignKey(
        Topic,
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

    subject = models.CharField(max_length=255)
    slug = AutoSlugField(populate_from="subject", max_length=255)

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
