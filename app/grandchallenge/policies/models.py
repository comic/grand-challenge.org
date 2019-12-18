from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel
from simple_history.models import HistoricalRecords

from grandchallenge.subdomains.utils import reverse


class Policy(TitleSlugDescriptionModel):
    body = models.TextField()
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("policies:detail", kwargs={"slug": self.slug})
