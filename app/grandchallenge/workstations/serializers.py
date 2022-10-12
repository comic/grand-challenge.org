from rest_framework.fields import CharField, URLField
from rest_framework.relations import HyperlinkedRelatedField
from rest_framework.serializers import ModelSerializer

from grandchallenge.workstations.models import Feedback, Session, Workstation


class SessionSerializer(ModelSerializer):
    status = CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Session
        fields = ("pk", "status")


class FeedbackSerializer(ModelSerializer):
    session = HyperlinkedRelatedField(
        queryset=Session.objects.all(), view_name="api:session-detail"
    )

    class Meta:
        model = Feedback
        fields = ("session", "screenshot", "user_comment", "context")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user
            self.fields["session"].queryset = Session.objects.filter(
                creator=user
            ).all()


class WorkstationSerializer(ModelSerializer):
    url = URLField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Workstation
        fields = ("pk", "title", "slug", "url")
