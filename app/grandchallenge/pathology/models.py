from django.db import models
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.worklists.models import Worklist

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel


class WorklistItem(UUIDModel):
    worklist = models.ForeignKey("Worklist", null=False, blank=False, on_delete=models.CASCADE)
    image = models.ForeignKey('Image', null=False, blank=False, on_delete=models.CASCADE)


class PatientItem(UUIDModel):
    patient = models.ForeignKey("Patient", null=False, blank=False, on_delete=models.CASCADE)
    study = models.foreignKey("Study", null=False, blank=False, on_delete=models.CASCADE)


class StudyItem(UUIDModel):
    study = models.ForeignKey("Study", null=False, blank=False, on_delete=models.CASCADE)
    image = models.ForeignKey('Image', null=False, blank=False, on_delete=models.CASCADE)
