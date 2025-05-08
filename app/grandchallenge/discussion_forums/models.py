from django.contrib.auth import get_user_model
from django.db import models
from django.utils.functional import cached_property
from django_extensions.db.fields import AutoSlugField

from grandchallenge.core.models import UUIDModel


class TopicTypeChoices(models.TextChoices):
    DEFAULT = "DEFAULT", "Default topic"
    STICKY = "STICKY", "Sticky topic"
    ANNOUNCE = "ANNOUNCE", "Announcement topic"


class Forum(UUIDModel):
    # name gets populated from challenge title, so use same max_length
    name = models.CharField(max_length=60)
    slug = AutoSlugField(populate_from="name", max_length=60)

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
        return self.name


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

    @cached_property
    def first_post(self):
        return self.posts.all().order_by("created").first()


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
