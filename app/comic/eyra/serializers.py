from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from guardian.shortcuts import get_perms
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.reverse import reverse

from comic.eyra.models import Algorithm, Job, Benchmark, Submission, DataFile, DataSet


class Permissions(serializers.Field):
    def to_representation(self, instance):
        user = self.context['request'].user
        return get_perms(user, instance)

    class Meta:
        swagger_schema_fields = {
            'type': 'array',
            'items': {'type': 'integer'}
        }


class AlgorithmSerializer(serializers.ModelSerializer):
    creator = PrimaryKeyRelatedField(read_only=True)
    permissions = Permissions(source="*", read_only=True)

    class Meta:
        model = Algorithm
        fields = [*[f.name for f in Algorithm._meta.fields], 'permissions']


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'


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


class FileField(serializers.FileField):
    def to_representation(self, value):
        return reverse('api:data_files-download', kwargs={'pk': value.instance.id}, request=self.context['request'])


class DataFileSerializer(serializers.ModelSerializer):
    file = FileField()

    class Meta:
        model = DataFile
        fields = '__all__'

    def update(self, instance, validated_data):
        if 'type' in validated_data:
            raise serializers.ValidationError({
                'type': 'Type cannot be changed.',
            })

        return super().update(instance, validated_data)


class DataSetSerializer(serializers.ModelSerializer):
    # files = DataSetTypeFilesSerializer(many=True)
    class Meta:
        model = DataSet
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['username'] = validated_data['email']
        user = super().create(validated_data)
        return user

    def to_representation(self, instance):
        return UserSerializer(instance).data


class UserSerializer(serializers.ModelSerializer):
    # groups = serializers.HyperlinkedRelatedField(
    #     many=True, view_name="api:group-detail", read_only=True
    # )

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'groups')


class GroupSerializer(serializers.ModelSerializer):
    user_set = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all()
    )

    class Meta:
        model = Group
        fields = ("id", "name", "user_set")
