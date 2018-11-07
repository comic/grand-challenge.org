from django.db import models
from django.utils.translation import ugettext_lazy as _

from grandchallenge.core.models import UUIDModel


class Study(UUIDModel):
    code = models.CharField(_("The identifier code for this study."), null=False, blank=False, max_length=100)
    region_of_interest = models.CharField(_("Region or location where the study was performed."),
                                          null=False,
                                          blank=False,
                                          max_length=255)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Study._meta.fields]
