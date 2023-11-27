from rest_framework import serializers

from grandchallenge.incentives.models import Incentive


class IncentiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incentive
        fields = ("incentive",)
