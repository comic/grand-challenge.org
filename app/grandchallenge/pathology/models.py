from django.db import models
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.worklists.models import Worklist

from grandchallenge.core.models import UUIDModel


class WorklistItems(UUIDModel):
    worklist = models.ForeignKey("Worklist", null=False, blank=False, on_delete=models.CASCADE)
    study = models.ForeignKey("Study", null=False, blank=False, on_delete=models.CASCADE)


class PatientItems(UUIDModel):
    patient = models.ForeignKey("Patient", null=False, blank=False, on_delete=models.CASCADE)
    study = models.foreignKey("Study", null=False, blank=False, on_delete=models.CASCADE)


class StudyItems(UUIDModel):
    study = models.ForeignKey("Study", null=False, blank=False, on_delete=models.CASCADE)
    #TODO: Add dataset without annotations here
