from django.db import models
from django.utils.translation import ugettext_lazy as _


class Patient(models.Model):
    SexChoices = (('M', 'Male'),
                 ('F', 'Female'),
                 ('O', 'Other'))

    name = models.CharField(_("Name of Patient"), null=False, blank=False, max_length=255)
    sex = models.CharField(max_length=1, choices=SexChoices, default='O')
    height = models.IntegerField(null=False, blank=False)