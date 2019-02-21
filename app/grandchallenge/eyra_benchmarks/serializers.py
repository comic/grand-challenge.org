from django.contrib.auth.models import User
from rest_framework import serializers

from grandchallenge.eyra_benchmarks.models import Benchmark
from grandchallenge.eyra_datasets.models import DataSet


class BenchmarkSerializer(serializers.HyperlinkedModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    datasets = serializers.PrimaryKeyRelatedField(many=True, queryset=DataSet.objects.all())
    # participants_group = serializers.PrimaryKeyRelatedField()
    # admins_group = serializers.PrimaryKeyRelatedField()

    class Meta:
        model = Benchmark
        fields = (
            "pk",
            "datasets",
            "title",
            "description",
            "creator",
        )
