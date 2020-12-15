from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.fields import AutoSlugField
from simple_history.models import HistoricalRecords

from grandchallenge.core.storage import get_logo_path, public_s3_storage
from grandchallenge.subdomains.utils import reverse


class Post(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=1024)
    slug = AutoSlugField(populate_from="title", max_length=1024)
    description = models.TextField()
    content = models.TextField()

    authors = models.ManyToManyField(
        to=get_user_model(), related_name="blog_authors"
    )

    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage,
    )

    published = models.BooleanField(default=False)

    history = HistoricalRecords()

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blogs:detail", kwargs={"slug": self.slug})
