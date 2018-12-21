from rest_framework import serializers

from .models import OctObsRegistration


class OctObsRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OctObsRegistration
        fields = ("obs_image", "oct_image", "registration_values")
