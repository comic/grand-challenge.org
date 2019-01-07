from rest_framework import serializers

from grandchallenge.challenges.models import Challenge


class ChallengeSerializer(serializers.HyperlinkedModelSerializer):
    creator = serializers.HyperlinkedRelatedField(
        view_name="api:user-detail", read_only=True
    )
    participants_group = serializers.HyperlinkedRelatedField(
        view_name="api:group-detail", read_only=True
    )
    admins_group = serializers.HyperlinkedRelatedField(
        view_name="api:group-detail", read_only=True
    )

    class Meta:
        model = Challenge
        fields = (
            "pk",
            "short_name",
            "description",
            "require_participant_review",
            "use_evaluation",
            "creator",
            "participants_group",
            "admins_group",
        )
