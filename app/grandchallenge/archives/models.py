from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, remove_perm
from stdimage import JPEGField

from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.components.models import (
    CIVForObjectMixin,
    CIVSetObjectPermissionsMixin,
    CIVSetStringRepresentationMixin,
    ComponentInterfaceValue,
    ValuesForInterfacesMixin,
)
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.core.utils.access_requests import (
    AccessRequestHandlingOptions,
    process_access_request,
)
from grandchallenge.hanging_protocols.models import HangingProtocolMixin
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse


class Archive(
    UUIDModel,
    TitleSlugDescriptionModel,
    HangingProtocolMixin,
    ValuesForInterfacesMixin,
):
    """Model for archive. Contains a collection of images."""

    detail_page_markdown = models.TextField(blank=True)
    logo = JPEGField(
        upload_to=get_logo_path,
        storage=public_s3_storage,
        variations=settings.STDIMAGE_LOGO_VARIATIONS,
    )
    social_image = JPEGField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this archive which is displayed when you post the link to this archive on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
        variations=settings.STDIMAGE_SOCIAL_VARIATIONS,
    )
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="editors_of_archive",
    )
    uploaders_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="uploaders_of_archive",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.PROTECT,
        editable=False,
        related_name="users_of_archive",
    )
    public = models.BooleanField(default=False)
    access_request_handling = models.CharField(
        max_length=25,
        choices=AccessRequestHandlingOptions.choices,
        default=AccessRequestHandlingOptions.MANUAL_REVIEW,
        help_text=("How would you like to handle access requests?"),
    )
    workstation = models.ForeignKey(
        "workstations.Workstation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    optional_hanging_protocols = models.ManyToManyField(
        "hanging_protocols.HangingProtocol",
        through="OptionalHangingProtocolArchive",
        related_name="optional_for_archive",
        blank=True,
        help_text="Optional alternative hanging protocols for this archive",
    )
    publications = models.ManyToManyField(
        Publication,
        blank=True,
        help_text="The publications associated with this archive",
    )
    modalities = models.ManyToManyField(
        ImagingModality,
        blank=True,
        help_text="The imaging modalities contained in this archive",
    )
    structures = models.ManyToManyField(
        BodyStructure,
        blank=True,
        help_text="The structures contained in this archive",
    )
    organizations = models.ManyToManyField(
        Organization,
        blank=True,
        help_text="The organizations associated with this archive",
        related_name="archives",
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created",)
        permissions = [
            (
                "use_archive",
                (
                    "Can use the objects in the archive as inputs to "
                    "algorithms, reader studies and challenges."
                ),
            ),
            ("upload_archive", "Can upload to archive"),
        ]

    def __str__(self):
        return f"{self.title}"

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()

        super().save(*args, **kwargs)

        self.assign_permissions()

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.uploaders_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_uploaders"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def assign_permissions(self):
        # Allow the editors, uploaders and users groups to view this
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(
            f"view_{self._meta.model_name}", self.uploaders_group, self
        )
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)

        # Allow the editors, uploaders and users group to use the archive
        assign_perm(f"use_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"use_{self._meta.model_name}", self.uploaders_group, self)
        assign_perm(f"use_{self._meta.model_name}", self.users_group, self)

        # Allow editors and uploaders to upload to this
        assign_perm(
            f"upload_{self._meta.model_name}", self.editors_group, self
        )
        assign_perm(
            f"upload_{self._meta.model_name}", self.uploaders_group, self
        )
        # Allow the editors to change this
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", reg_and_anon, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", reg_and_anon, self)

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        return user.groups.add(self.editors_group)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_uploader(self, user):
        return user.groups.filter(pk=self.uploaders_group.pk).exists()

    def add_uploader(self, user):
        return user.groups.add(self.uploaders_group)

    def remove_uploader(self, user):
        return user.groups.remove(self.uploaders_group)

    def is_user(self, user):
        return user.groups.filter(pk=self.users_group.pk).exists()

    def add_user(self, user):
        return user.groups.add(self.users_group)

    def remove_user(self, user):
        return user.groups.remove(self.users_group)

    def get_absolute_url(self):
        return reverse("archives:detail", kwargs={"slug": self.slug})

    @property
    def api_url(self) -> str:
        return reverse("api:archive-detail", kwargs={"pk": self.pk})

    @property
    def civ_sets_list_url(self):
        return reverse("archives:items-list", kwargs={"slug": self.slug})

    @property
    def list_url(self):
        return reverse("archives:list")

    @property
    def bulk_delete_url(self):
        return reverse(
            "archives:items-bulk-delete",
            kwargs={"slug": self.slug},
        )

    @property
    def interface_viewname(self):
        return "components:component-interface-list-archives"

    @property
    def civ_sets_related_manager(self):
        return self.items

    @property
    def civ_set_model(self):
        return ArchiveItem

    def create_civ_set(self, data):
        return self.civ_set_model.objects.create(archive=self, **data)

    @property
    def create_civ_set_url(self):
        return reverse("archives:item-create", kwargs={"slug": self.slug})

    @property
    def create_civ_set_batch_url(self):
        return reverse("archives:cases-create", kwargs={"slug": self.slug})

    @cached_property
    def allowed_socket_slugs(self):
        if self.phase_set.count() != 0:
            allowed_slugs = []
            for phase in self.phase_set.all():
                allowed_slugs.extend(
                    [
                        inp.slug
                        for interface in phase.algorithm_interfaces.all()
                        for inp in interface.inputs.all()
                    ]
                )
            return set(allowed_slugs)
        else:
            raise AttributeError


class ArchiveUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(Archive, on_delete=models.CASCADE)


class ArchiveGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_archive", "view_archive", "upload_archive", "use_archive"}
    )

    content_object = models.ForeignKey(Archive, on_delete=models.CASCADE)


class ArchiveItem(
    CIVSetStringRepresentationMixin,
    CIVSetObjectPermissionsMixin,
    CIVForObjectMixin,
    UUIDModel,
):
    archive = models.ForeignKey(
        Archive, related_name="items", on_delete=models.PROTECT
    )
    values = models.ManyToManyField(
        ComponentInterfaceValue, blank=True, related_name="archive_items"
    )
    title = models.CharField(max_length=255, default="", blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["title", "archive"],
                name="unique_archive_item_title",
                condition=~Q(title=""),
            )
        ]

    def assign_permissions(self):
        # Archive editors, uploaders and users can view this archive item
        assign_perm(self.view_perm, self.archive.editors_group, self)
        assign_perm(self.view_perm, self.archive.uploaders_group, self)
        assign_perm(self.view_perm, self.archive.users_group, self)

        # Archive editors and uploaders can change this archive item
        assign_perm(self.change_perm, self.archive.editors_group, self)
        assign_perm(
            self.change_perm,
            self.archive.uploaders_group,
            self,
        )

        # Archive editors can delete this archive item
        assign_perm(
            self.delete_perm,
            self.archive.editors_group,
            self,
        )

    @property
    def base_object(self):
        return self.archive

    @property
    def update_url(self):
        return reverse(
            "archives:item-edit",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    @property
    def delete_url(self):
        return reverse(
            "archives:item-delete",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    def get_absolute_url(self):
        return reverse(
            "archives:item-detail",
            kwargs={"slug": self.base_object.slug, "pk": self.pk},
        )

    @property
    def is_editable(self):
        return True

    def add_civ(self, *, civ):
        super().add_civ(civ=civ)
        return self.values.add(civ)

    def remove_civ(self, *, civ):
        super().remove_civ(civ=civ)
        return self.values.remove(civ)

    def get_civ_for_interface(self, interface):
        return self.values.get(interface=interface)


class ArchiveItemUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(ArchiveItem, on_delete=models.CASCADE)


class ArchiveItemGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_archiveitem", "delete_archiveitem", "view_archiveitem"}
    )

    content_object = models.ForeignKey(ArchiveItem, on_delete=models.CASCADE)


class ArchivePermissionRequest(RequestBase):
    """
    When a user wants to view an archive, editors have the option of
    reviewing each user before accepting or rejecting them. This class records
    the needed info for that.
    """

    archive = models.ForeignKey(
        Archive,
        help_text="To which archive has the user requested access?",
        on_delete=models.CASCADE,
    )
    rejection_text = models.TextField(
        blank=True,
        help_text=(
            "The text that will be sent to the user with the reason for their "
            "rejection."
        ),
    )

    @property
    def base_object(self):
        return self.archive

    @property
    def object_name(self):
        return self.base_object.title

    @property
    def add_method(self):
        return self.base_object.add_user

    @property
    def remove_method(self):
        return self.base_object.remove_user

    @property
    def permission_list_url(self):
        return reverse(
            "archives:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )

    def __str__(self):
        return f"{self.object_name} registration request by user {self.user.username}"

    def save(self, *args, **kwargs):
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            process_access_request(request_object=self)

    class Meta(RequestBase.Meta):
        unique_together = (("archive", "user"),)


class OptionalHangingProtocolArchive(models.Model):
    # Through table for optional hanging protocols
    # https://docs.djangoproject.com/en/4.2/topics/db/models/#intermediary-manytomany
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE)
    hanging_protocol = models.ForeignKey(
        "hanging_protocols.HangingProtocol", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (("archive", "hanging_protocol"),)
