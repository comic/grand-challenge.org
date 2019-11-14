from rest_framework import serializers

from grandchallenge.patients.models import Patient
from grandchallenge.studies.models import Study


class StudySerializer(serializers.ModelSerializer):
    # allow parent relation to be empty for validation purposes
    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), required=False
    )

    def get_unique_together_validators(self):
        """Overriding method to disable unique together checks."""
        return []

    class Meta:
        model = Study
        fields = ("id", "name", "datetime", "patient")
