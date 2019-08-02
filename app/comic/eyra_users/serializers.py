from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from guardian.shortcuts import get_perms
from rest_framework import serializers


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


class Permissions(serializers.Field):
    def to_representation(self, instance):
        user = self.context['request'].user
        return get_perms(user, instance)

    class Meta:
        swagger_schema_fields = {
            'type': 'array',
            'items': {'type': 'integer'}
        }