import logging

from django.db import models
from django.utils.text import slugify

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


class Algorithm(UUIDModel):
    title = models.CharField(max_length=32, unique=True, null=True)
    slug = models.SlugField(
        max_length=32, editable=False, unique=True, null=True
    )
    mlmodel = models.ForeignKey("mlmodels.MLModel", on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"slug": self.slug})
