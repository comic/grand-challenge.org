from django_countries.serializer_fields import CountryField
from rest_framework import serializers
from rest_framework.fields import URLField

from grandchallenge.evaluation.serializers import UserSerializer
from grandchallenge.profiles.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    location = CountryField(source="country")
    mugshot = URLField(source="mugshot.x20.url", read_only=True, default="")

    class Meta:
        model = UserProfile
        fields = (
            "user",
            "mugshot",
            "institution",
            "department",
            "location",
            "website",
        )
