from rest_framework import serializers

from django.contrib.auth.models import User, Group


class UserSerializer(serializers.ModelSerializer):
    # groups = serializers.HyperlinkedRelatedField(
    #     many=True, view_name="api:group-detail", read_only=True
    # )

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'groups')


class GroupSerializer(serializers.ModelSerializer):
    # user_set = serializers.PrimaryKeyRelatedField(
    #     many=True, view_name="api:user-detail", read_only=True
    # )

    class Meta:
        model = Group
        fields = ("name",)
