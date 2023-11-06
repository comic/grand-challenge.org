from rest_framework import serializers
from rest_framework.fields import URLField

from grandchallenge.challenges.models import Challenge


class ChallengeSerializer(serializers.ModelSerializer):
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Challenge
        fields = [
            "api_url",
            "url",
            "slug",
        ]
