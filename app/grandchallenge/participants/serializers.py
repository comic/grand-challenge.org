from grandchallenge.participants.models import (
    RegistrationQuestionAnswer,
)
from rest_framework.serializers import (
    ModelSerializer,
)
from rest_framework.fields import SerializerMethodField, CharField


class RegistrationQuestionAnswersSerializer(ModelSerializer):
    user = CharField(
        source="registration_request.user.username",
        read_only=True,
    )
    registration_status = SerializerMethodField(read_only=True)
    question_text = CharField(
        source="question.question_text",
        read_only=True,
    )

    class Meta:
        model = RegistrationQuestionAnswer
        fields = (
            "user",
            "registration_status",
            "question_text",
            "answer",
        )

    def get_registration_status(self, obj):
        return obj.registration_request.get_status_display()
