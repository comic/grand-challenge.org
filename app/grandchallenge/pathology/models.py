from django.db import models
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.worklists.models import Worklist

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel


class PatientItem(UUIDModel):
    patient = models.ForeignKey(
        "patients.Patient", null=False, blank=False, on_delete=models.CASCADE
    )
    study = models.ForeignKey(
        "studies.Study", null=False, blank=False, on_delete=models.CASCADE
    )


class StudyItem(UUIDModel):
    study = models.ForeignKey(
        "studies.Study", null=False, blank=False, on_delete=models.CASCADE
    )
    image = models.ForeignKey(
        "cases.Image", null=False, blank=False, on_delete=models.CASCADE
    )


class WorklistItem(UUIDModel):
    worklist = models.ForeignKey(
        "worklists.Worklist", null=False, blank=False, on_delete=models.CASCADE
    )
    image = models.ForeignKey(
        "cases.Image", null=False, blank=False, on_delete=models.CASCADE
    )
