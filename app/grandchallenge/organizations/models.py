from django.contrib.auth.models import Group
from django.db import models
from django_countries.fields import CountryField

from grandchallenge.core.models import (
    TimeStampedModel,
    TitleSlugDescriptionModel,
)
from grandchallenge.core.storage import get_logo_path, public_s3_storage


class Organization(TitleSlugDescriptionModel, TimeStampedModel):
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage
    )
    location = CountryField()
    website = models.URLField()

    detail_page_markdown = models.TextField(blank=True)

    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="editors_of_organization",
    )
    members_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="members_of_organization",
    )

    class Meta(TitleSlugDescriptionModel.Meta, TimeStampedModel.Meta):
        pass
