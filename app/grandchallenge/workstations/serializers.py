from rest_framework.fields import CharField, URLField
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.workstations.models import Feedback, Session


class SessionSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = ("pk", "status")


class FeedbackSerializer(ModelSerializer):
    session = HyperlinkedRelatedField(
        read_only=True, view_name="api:session-detail"
    )
    screenshot = URLField(source="screenshot.url", read_only=True)

    class Meta:
        model = Feedback
        fields = ("session", "screenshot", "user_comment", "context")
