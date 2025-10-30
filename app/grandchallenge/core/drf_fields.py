from django.utils.duration import duration_iso_string
from rest_framework.fields import DurationField


class ISODurationField(DurationField):
    # TODO - This functionality will in DRF 3.17, remove when released
    def to_representation(self, value):
        return duration_iso_string(value)
