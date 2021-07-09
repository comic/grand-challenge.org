from pytz import all_timezones
from rest_framework.fields import ChoiceField
from rest_framework.serializers import Serializer


class TimezoneSerializer(Serializer):
    timezone = ChoiceField(choices=all_timezones, required=True)
