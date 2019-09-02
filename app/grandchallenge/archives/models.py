from django.db import models
from django.db.models import Count

from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study


class Archive(UUIDModel):
    """
    Model for archive. Contains a collection of images
    """

    name = models.CharField(max_length=255, default="Unnamed Archive")

    images = models.ManyToManyField(Image)

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    def delete(self, *args, **kwargs):
        """
        Removes all patients, studies, images, imagefiles and annotations that belong
        exclusively to this archive
        """
        images_to_remove = (
            Image.objects.annotate(num_archives=Count("archive"))
            .filter(archive__id=self.id, num_archives=1)
            .all()
        )
        protected_study_ids = set()
        protected_patient_ids = set()
        for image in images_to_remove:
            if image.study is None:
                continue
            for image1 in image.study.image_set.all():
                if image1 not in images_to_remove:
                    protected_study_ids.add(image.study.id)
                    protected_patient_ids.add(image.study.patient.id)
                    break

        related_patients = Patient.objects.filter(
            study__image__in=images_to_remove
        ).distinct()
        related_studies = Study.objects.filter(
            image__in=images_to_remove
        ).distinct()
        for patient in related_patients:
            if patient.id not in protected_patient_ids:
                patient.delete(*args, **kwargs)
        for study in related_studies:
            if study.id not in protected_study_ids:
                study.delete(*args, **kwargs)

        images_to_remove.delete(*args, **kwargs)

        super().delete(*args, **kwargs)
