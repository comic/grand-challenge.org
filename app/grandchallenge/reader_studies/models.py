from django.contrib.auth import get_user_model
from django.db import models
from django_extensions.db.models import TitleSlugDescriptionModel

from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


class ReaderStudy(UUIDModel, TitleSlugDescriptionModel):
    creator = models.ForeignKey(
        get_user_model(), null=True, on_delete=models.SET_NULL
    )
    readers = models.ManyToManyField(
        get_user_model(), related_name="readerstudies"
    )
    images = models.ManyToManyField(
        "cases.Image", related_name="readerstudies"
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        verbose_name_plural = "reader studies"

    def get_absolute_url(self):
        return reverse("reader-studies:detail", kwargs={"slug": self.slug})
