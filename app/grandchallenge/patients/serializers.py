from rest_framework import serializers

from grandchallenge.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    def get_unique_together_validators(self):
        """Overriding method to disable unique together checks."""
        return []

    class Meta:
        model = Patient
        fields = ("id", "name")
