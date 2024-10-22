from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet

from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from grandchallenge.participants.renderers import (
    RegistrationRequestCSVRenderer,
)
from grandchallenge.participants.serializers import (
    RegistrationRequestSerializer,
)


class RegistrationRequestViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = RegistrationRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["challenge__short_name"]
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        RegistrationRequestCSVRenderer,
    )

    def get_queryset(self):
        viewable_challenges = filter_by_permission(
            queryset=Challenge.objects.all(),
            user=self.request.user,
            codename="change_challenge",
            accept_user_perms=False,
        )

        # Permission check on challenges
        queryset = RegistrationRequest.objects.filter(
            challenge__in=viewable_challenges
        )

        viewable_questions = filter_by_permission(
            queryset=RegistrationQuestion.objects.filter(
                challenge__in=viewable_challenges
            ).all(),
            user=self.request.user,
            codename="view_registrationquestion",
            accept_user_perms=False,
        )

        # Prefetch with filter for viewable questions
        queryset = queryset.prefetch_related(
            Prefetch(
                "registration_question_answers",
                RegistrationQuestionAnswer.objects.filter(
                    question__in=viewable_questions
                ),
            ),
            "registration_question_answers__question",
        )

        return queryset.select_related(
            "user__user_profile",
        ).order_by("created")
