from django.contrib.auth.models import Group
from django.db import models, transaction
from django.db.models import Count
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import Image
from grandchallenge.challenges.models import get_logo_path
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study


class Archive(UUIDModel, TitleSlugDescriptionModel):
    """Model for archive. Contains a collection of images."""

    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage, null=True
    )
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="editors_of_archive",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="users_of_archive",
    )
    public = models.BooleanField(default=False)
    images = models.ManyToManyField(Image)

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

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def assign_permissions(self):
        # Allow the editors and users groups to view this
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Allow the editors to change this
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

        # TODO: Handle public permissions

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
