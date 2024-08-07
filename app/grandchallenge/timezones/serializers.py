import zoneinfo

from rest_framework.fields import ChoiceField
from rest_framework.serializers import Serializer


class TimezoneSerializer(Serializer):
    timezone = ChoiceField(
        choices=sorted(zoneinfo.available_timezones()), required=True
    )
