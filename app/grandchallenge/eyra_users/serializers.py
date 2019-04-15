from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from rest_framework import serializers

from grandchallenge.api.serializers import UserSerializer
from grandchallenge.profiles.social_auth.pipeline.profile import create_profile, add_to_default_group


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['username'] = validated_data['email']
        user = super().create(validated_data)
        create_profile(user, True)
        add_to_default_group(user, True)
        return user

    def to_representation(self, instance):
        return UserSerializer(instance).data
