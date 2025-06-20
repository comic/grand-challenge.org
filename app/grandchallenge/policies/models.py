from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.subdomains.utils import reverse


class Policy(TitleSlugDescriptionModel):
    body = models.TextField()

    def __str__(self):
        return f"{self.title}"

    class Meta(TitleSlugDescriptionModel.Meta):
        ordering = ("pk",)

    def get_absolute_url(self):
        return reverse("policies:detail", kwargs={"slug": self.slug})
