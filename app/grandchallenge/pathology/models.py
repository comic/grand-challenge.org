from django.db import models
from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study
from grandchallenge.worklists.models import Worklist


class WorklistItems(models.Model):
    worklist = models.ForeignKey('Worklist', null=False, blank=False, on_delete=models.CASCADE)
    study = models.ForeignKey('Study', null=False, blank=False, on_delete=models.CASCADE)


class PatientItems(models.Model):
    patient = models.ForeignKey('Patient', null=False, blank=False, on_delete=models.CASCADE)
    study = models.foreignKey('Study', null=False, blank=False, on_delete=models.CASCADE)


class StudyItems(models.Model):
    study = models.ForeignKey('Study', null=False, blank=False, on_delete=models.CASCADE)
    #TODO: Add dataset without annotations here
