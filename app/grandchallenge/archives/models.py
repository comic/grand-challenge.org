from django.db import models, transaction
from django.db.models import Count

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study


class Archive(UUIDModel):
    """Model for archive. Contains a collection of images."""

    name = models.CharField(max_length=255, default="Unnamed Archive")

    images = models.ManyToManyField(Image)

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"

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
            .filter(archive__id=self.id, num_archives=1)
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
