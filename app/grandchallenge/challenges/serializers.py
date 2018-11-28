from rest_framework import serializers

from grandchallenge.challenges.models import Challenge


class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = (
            "pk",
            "short_name",
            "description",
            "require_participant_review",
            "use_evaluation",
            "creator",
        )
