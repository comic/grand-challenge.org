from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.filters import BaseFilterBackend
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet

from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.participants.filters import RegistrationRequestFilter
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.participants.renderers import (
    RegistrationRequestCSVRenderer,
)
from grandchallenge.participants.serializers import (
    RegistrationRequestSerializer,
)


class CanViewRegistrationRequestFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        viewable_challenges = filter_by_permission(
            queryset=Challenge.objects.all(),
            user=request.user,
            codename="change_challenge",
            accept_user_perms=False,
        )

        return queryset.filter(challenge__in=viewable_challenges)


class RegistrationRequestViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = RegistrationRequestSerializer
    queryset = (
        RegistrationRequest.objects.select_related(
            "user__user_profile",
        )
        .prefetch_related("registration_question_answers__question")
        .order_by("created")
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, CanViewRegistrationRequestFilter]
    filterset_class = RegistrationRequestFilter
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        RegistrationRequestCSVRenderer,
    )
