from rest_framework import serializers

from grandchallenge.evaluation.models import Submission


class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api:submission-detail"
    )
    creator = serializers.SlugRelatedField(
        read_only=True, slug_field="username"
    )
    challenge = serializers.SlugRelatedField(
        read_only=True, slug_field="short_name"
    )

    class Meta:
        model = Submission
        fields = "__all__"
