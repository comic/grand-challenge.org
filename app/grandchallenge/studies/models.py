from django.db import models
from django.utils.translation import ugettext_lazy as _


class Study(models.Model):
    region_of_interest = models.CharField(_("Region or location where the study was performed."),
                                          null=False,
                                          blank=False,
                                          max_length=255)
