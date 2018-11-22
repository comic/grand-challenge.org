from django.db import models
from django.utils.translation import ugettext_lazy as _

from grandchallenge.core.models import UUIDModel


class Patient(UUIDModel):
    SexChoices = (('M', 'Male'),
                  ('F', 'Female'),
                  ('O', 'Other'))

    name = models.CharField(_("Name of Patient"), null=False, blank=False, max_length=255)
    sex = models.CharField(max_length=1, choices=SexChoices, default='O')
    height = models.IntegerField(null=False, blank=False)

    def get_fields(self):
        return [(field, field.value_to_string(self)) for field in Patient._meta.fields]

    def __str__(self):
        return "%s (%s)" % (self.name, str(self.id))
