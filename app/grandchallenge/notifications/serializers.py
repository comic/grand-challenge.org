from actstream.models import Follow
from rest_framework import serializers

from grandchallenge.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("read",)


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("pk", "flag")
