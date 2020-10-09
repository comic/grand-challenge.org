from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers

from grandchallenge.core.serializers import UserSerializer
from grandchallenge.profiles.models import UserProfile


class UserProfileSerializer(CountryFieldMixin, serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = UserProfile
        fields = (
            "user",
            "mugshot",
            "privacy",
            "institution",
            "department",
            "country",
            "website",
        )
