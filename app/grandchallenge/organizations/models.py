from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django_countries.fields import CountryField
from guardian.shortcuts import assign_perm
from stdimage import JPEGField

from grandchallenge.core.models import (
    TitleSlugDescriptionModel,
    UUIDModel,
)
from grandchallenge.core.storage import get_logo_path, public_s3_storage
from grandchallenge.subdomains.utils import reverse


class Organization(TitleSlugDescriptionModel, UUIDModel):
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    location = CountryField()
    website = models.URLField()

    detail_page_markdown = models.TextField(blank=True)

    editors_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="editors_of_organization",
    )
    members_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="members_of_organization",
    )

    class Meta(TitleSlugDescriptionModel.Meta, UUIDModel.Meta):
        ordering = ("created",)

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("organizations:detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self._create_groups()

        super().save(*args, **kwargs)

        if adding:
            self._assign_permissions()

    def _create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.members_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_members"
        )

    def _assign_permissions(self):
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_member(self, user):
        return user.groups.filter(pk=self.members_group.pk).exists()

    def add_member(self, user):
        return user.groups.add(self.members_group)

    def remove_member(self, user):
        return user.groups.remove(self.members_group)
