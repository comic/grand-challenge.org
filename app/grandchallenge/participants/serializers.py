from rest_framework.fields import CharField, SerializerMethodField
from rest_framework.serializers import ModelSerializer

from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from grandchallenge.profiles.serializers import UserProfileSerializer


class RegistrationQuestionSerializer(ModelSerializer):

    class Meta:
        model = RegistrationQuestion
        fields = (
            "question_text",
            "question_help_text",
            "required",
        )


class RegistrationQuestionAnswerSerializer(ModelSerializer):

    question = RegistrationQuestionSerializer()

    class Meta:
        model = RegistrationQuestionAnswer
        fields = (
            "question",
            "answer",
        )


class RegistrationRequestSerializer(ModelSerializer):
    challenge = CharField(read_only=True, source="challenge.short_name")
    user = UserProfileSerializer(read_only=True, source="user.user_profile")
    registration_status = SerializerMethodField(read_only=True)
    registration_question_answers = RegistrationQuestionAnswerSerializer(
        many=True
    )

    class Meta:
        model = RegistrationRequest
        fields = (
            "challenge",
            "user",
            "created",
            "changed",
            "registration_status",
            "registration_question_answers",
        )

    def get_registration_status(self, obj):
        return obj.get_status_display()
