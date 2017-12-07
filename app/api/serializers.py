from rest_framework import serializers

from evaluation.models import Result, Submission, Job, Method


class ResultSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api:result-detail")

    class Meta:
        model = Result
        fields = '__all__'


class SubmissionSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api:submission-detail")

    creator = serializers.SlugRelatedField(read_only=True,
                                           slug_field='username')
    challenge = serializers.SlugRelatedField(read_only=True,
                                             slug_field='short_name')

    class Meta:
        model = Submission
        fields = '__all__'


class JobSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api:job-detail")

    class Meta:
        model = Job
        fields = '__all__'


class MethodSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="api:method-detail")

    class Meta:
        model = Method
        fields = '__all__'
