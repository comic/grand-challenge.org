from rest_framework import serializers

from grandchallenge.challenges.models import Challenge


class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = [
            "api_url",
            "url",
            "slug",
        ]
