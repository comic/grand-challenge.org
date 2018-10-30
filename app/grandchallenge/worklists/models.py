from django.db import models
from django.db.models import CharField
from django.utils.translation import ugettext_lazy as _


class WorklistGroup(models.Model):
    title = CharField(_("Title of group"), null=False, blank=False, max_length=255)


class Worklist(models.Model):
    title = CharField(_("Title of Work list"), null=False, blank=False, max_length=255)
    group = models.ForeignKey('WorklistGroup', null=False, blank=False, on_delete=models.CASCADE)
    parent = models.ForeignKey('Worklist', null=True, blank=True, on_delete=models.CASCADE)
    #owner = models.ForeignKey(User, null=False, blank=False, on_delete=models.CASCADE)


#class WorklistPatientRelation(models.Model):
 #   worklist = models.ForeignKey('Worklist', null=False, blank=False, on_delete=models.CASCADE)
  #  patient = models.ForeignKey('Patient', null=False, blank=False, on_delete=models.CASCADE)
