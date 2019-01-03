from rest_framework import serializers

from django.contrib.auth.models import User, Group
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


class UserSerializer(serializers.HyperlinkedModelSerializer):
    groups = serializers.HyperlinkedRelatedField(
        many=True, view_name="api:group-detail", read_only=True
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "groups")


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    user_set = serializers.HyperlinkedRelatedField(
        many=True, view_name="api:user-detail", read_only=True
    )

    class Meta:
        model = Group
        fields = ("name", "user_set")
