from rest_framework import serializers
from grandchallenge.patients.models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id', 'name', 'sex', 'height')
