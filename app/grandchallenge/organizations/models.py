from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django_countries.fields import CountryField
from guardian.shortcuts import assign_perm
from stdimage import JPEGField

from grandchallenge.components.schemas import (
    SELECTABLE_GPU_TYPES_SCHEMA,
    GPUTypeChoices,
    get_default_gpu_type_choices,
)
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import (
    FieldChangeMixin,
    TitleSlugDescriptionModel,
    UUIDModel,
)
from grandchallenge.core.storage import get_logo_path, public_s3_storage
from grandchallenge.core.validators import JSONValidator
from grandchallenge.subdomains.utils import reverse


class Organization(FieldChangeMixin, TitleSlugDescriptionModel, UUIDModel):
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    logo_width = models.PositiveSmallIntegerField(editable=False, null=True)
    logo_height = models.PositiveSmallIntegerField(editable=False, null=True)

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

    exempt_from_base_costs = models.BooleanField(
        default=False,
        help_text=(
            "If true, members of this organization will not be charged for "
            "base costs."
        ),
    )

    algorithm_selectable_gpu_type_choices = models.JSONField(
        default=get_default_gpu_type_choices,
        help_text=(
            "The GPU type choices that members will be able to select for their "
            "algorithm inference jobs. Options are "
            f"{GPUTypeChoices.values}.".replace("'", '"')
        ),
        validators=[JSONValidator(schema=SELECTABLE_GPU_TYPES_SCHEMA)],
    )

    algorithm_maximum_settable_memory_gb = models.PositiveSmallIntegerField(
        default=settings.ALGORITHMS_MAX_MEMORY_GB,
        help_text=(
            "Maximum amount of main memory (DRAM) that members will be allowed to "
            "assign to algorithm inference jobs."
        ),
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


class OrganizationUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Organization, on_delete=models.CASCADE)


class OrganizationGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"change_organization"})

    content_object = models.ForeignKey(Organization, on_delete=models.CASCADE)
