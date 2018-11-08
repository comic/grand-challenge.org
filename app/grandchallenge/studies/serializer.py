from rest_framework import serializers
from grandchallenge.studies.models import Study


class StudySerializer(serializers.ModelSerializer):
    class Meta:
        model = Study
        fields = ("id", "code", "region_of_interest")
