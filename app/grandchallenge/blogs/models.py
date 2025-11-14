from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django_extensions.db.fields import AutoSlugField
from stdimage import JPEGField

from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import FieldChangeMixin, ImageDimensionsMixin
from grandchallenge.core.storage import get_logo_path, public_s3_storage
from grandchallenge.subdomains.utils import reverse


class Tag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = AutoSlugField(populate_from="name", max_length=200)

    def __str__(self):
        return self.name


class Post(FieldChangeMixin, ImageDimensionsMixin, models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=1024)
    slug = AutoSlugField(populate_from="title", max_length=1024)
    description = models.TextField()
    content = models.TextField()

    authors = models.ManyToManyField(
        to=get_user_model(), related_name="blog_authors"
    )

    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_SOCIAL_VARIATIONS,
    )
    logo_width = models.PositiveSmallIntegerField(editable=False, null=True)
    logo_height = models.PositiveSmallIntegerField(editable=False, null=True)

    tags = models.ManyToManyField(to=Tag, blank=True, related_name="posts")

    published = models.BooleanField(default=False)

    highlight = models.BooleanField(
        default=False,
        help_text="If selected, this blog post will appear in first position in the news carousel on the home page.",
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.title

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._published_orig = self.published

    def save(self, *args, **kwargs):
        if self._published_orig is False and self.published is True:
            self.created = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blogs:detail", kwargs={"slug": self.slug})

    @property
    def public(self):
        return self.published

    def add_author(self, user):
        self.authors.add(user)


class PostUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"change_post"})

    content_object = models.ForeignKey(Post, on_delete=models.CASCADE)


class PostGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Post, on_delete=models.CASCADE)
