from rest_framework import serializers
from pathology_worklist.api.models import Worklist, Patient, Study, Image, WorklistPatientRelation


class StudySerializer(serializers.ModelSerializer):
    class Meta:
        model = Study
        fields = ('id', 'region_of_interest')
