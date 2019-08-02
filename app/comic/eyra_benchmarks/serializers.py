from guardian.shortcuts import get_perms
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from comic.eyra_benchmarks.models import Benchmark, Submission
from comic.eyra_users.serializers import Permissions


class BenchmarkSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)
    permissions = Permissions(source="*", read_only=True)

    class Meta:
        model = Benchmark
        fields = [*[f.name for f in Benchmark._meta.fields], 'permissions']


class SubmissionSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)
    metrics = serializers.JSONField(required=False)

    class Meta:
        model = Submission
        fields = '__all__'
