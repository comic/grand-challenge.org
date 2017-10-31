from rest_framework import serializers

from evaluation.models import Result, Submission, Job, Method


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = '__all__'


class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.SlugRelatedField(read_only=True, slug_field='username')
    challenge = serializers.SlugRelatedField(read_only=True,
                                             slug_field='short_name')

    class Meta:
        model = Submission
        fields = '__all__'


class JobSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


class MethodSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Method
        fields = '__all__'
