from django_countries.serializer_fields import CountryField
from rest_framework import serializers

from grandchallenge.evaluation.serializers import UserSerializer
from grandchallenge.profiles.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    location = CountryField(source="country")

    class Meta:
        model = UserProfile
        fields = (
            "user",
            "mugshot",
            "privacy",
            "institution",
            "department",
            "location",
            "website",
        )
