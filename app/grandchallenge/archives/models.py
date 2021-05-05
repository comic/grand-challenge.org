from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models, transaction
from django.db.models import Count
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.anatomy.models import BodyStructure
from grandchallenge.cases.models import Image
from grandchallenge.components.models import ComponentInterfaceValue
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import (
    get_logo_path,
    get_social_image_path,
    public_s3_storage,
)
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.organizations.models import Organization
from grandchallenge.patients.models import Patient
from grandchallenge.publications.models import Publication
from grandchallenge.studies.models import Study
from grandchallenge.subdomains.utils import reverse


class Archive(UUIDModel, TitleSlugDescriptionModel):
    """Model for archive. Contains a collection of images."""

    detail_page_markdown = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage, null=True
    )
    social_image = models.ImageField(
        upload_to=get_social_image_path,
        storage=public_s3_storage,
        blank=True,
        help_text="An image for this archive which is displayed when you post the link to this archive on social media. Should have a resolution of 640x320 px (1280x640 px for best display).",
    )
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="editors_of_archive",
    )
    uploaders_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="uploaders_of_archive",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="users_of_archive",
    )
    public = models.BooleanField(default=False)
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
    images = models.ManyToManyField(Image)
    algorithms = models.ManyToManyField(
        Algorithm,
        blank=True,
        help_text="Algorithms that will be executed on all images in this archive",
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
        return f"<{self.__class__.__name__} {self.title}>"

    @property
    def name(self):
        # Include the read only name for legacy clients
        return self.title

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

    def delete(self, *args, **kwargs):
        """
        Remove all patients, studies, images, imagefiles and annotations that
        belong exclusively to this archive.
        """

        def find_protected_studies_and_patients(images):
            """
            Returns a tuple containing a set of Study ids and a set of Patient
            ids that are "protected". Where "protected" means that these Study
            and Patient objects contain images that are not in the given list
            of images. Therefore, when deleting an archive and it's related
            objects, these Study and Patient objects should not be deleted
            since that would also delete other images, because of the cascading
            delete behavior of the many-to-one relation.

            :param images: list of image objects that are going to be removed
            :return: tuple containing a set of Study ids and a set of Patient
            ids that should not be removed
            """
            protected_study_ids = set()
            protected_patient_ids = set()
            for image in images:
                if image.study is None:
                    continue
                for other_study_image in image.study.image_set.all():
                    if other_study_image not in images_to_remove:
                        protected_study_ids.add(image.study.id)
                        protected_patient_ids.add(image.study.patient.id)
                        break

            return protected_study_ids, protected_patient_ids

        images_to_remove = (
            Image.objects.annotate(num_archives=Count("archive"))
            .filter(archive=self, num_archives=1)
            .order_by("name")
        )

        (
            protected_study_ids,
            protected_patient_ids,
        ) = find_protected_studies_and_patients(images_to_remove)

        with transaction.atomic():
            Patient.objects.filter(
                study__image__in=images_to_remove
            ).distinct().exclude(pk__in=protected_patient_ids).delete(
                *args, **kwargs
            )
            Study.objects.filter(
                image__in=images_to_remove
            ).distinct().exclude(pk__in=protected_study_ids).delete(
                *args, **kwargs
            )
            images_to_remove.delete(*args, **kwargs)

            super().delete(*args, **kwargs)

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
    def api_url(self):
        return reverse("api:archive-detail", kwargs={"pk": self.pk})


class ArchiveItem(UUIDModel):
    archive = models.ForeignKey(
        Archive, related_name="items", on_delete=models.CASCADE
    )
    values = models.ManyToManyField(
        ComponentInterfaceValue, blank=True, related_name="archive_items"
    )

    def delete(self, *args, **kwargs):
        image_pks = self.values.filter(image__isnull=False).values_list(
            "image", flat=True
        )
        images = Image.objects.filter(pk__in=image_pks)
        remove_perm("view_image", self.archive.editors_group, images)
        remove_perm("view_image", self.archive.uploaders_group, images)
        remove_perm("view_image", self.archive.users_group, images)

        super().delete(*args, **kwargs)


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

    class Meta(RequestBase.Meta):
        unique_together = (("archive", "user"),)
