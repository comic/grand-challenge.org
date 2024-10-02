import csv
from django.http import HttpResponse
from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.participants.filters import (
    RegistrationQuestionAnswerFilter,
)
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
)

from grandchallenge.participants.serializers import (
    RegistrationQuestionAnswersSerializer,
)
from rest_framework.permissions import DjangoObjectPermissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_guardian.filters import ObjectPermissionsFilter
from rest_framework.settings import api_settings
from rest_framework import mixins, viewsets
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from rest_framework.filters import BaseFilterBackend


class CanViewRegistrationQuestionFilter(BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        return queryset.filter(
            question__in=filter_by_permission(
                queryset=RegistrationQuestion.objects.filter(
                    answers__in=queryset
                ),
                user=request.user,
                codename="view_registrationquestion",
                accept_user_perms=False,
            )
        )


class RegistrationQuestionAnswerViewSet(mixins.ListModelMixin, GenericViewSet):
    serializer_class = RegistrationQuestionAnswersSerializer
    queryset = RegistrationQuestionAnswer.objects.all().select_related(
        "question__challenge",
        "registration_request",
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, CanViewRegistrationQuestionFilter]
    filterset_class = RegistrationQuestionAnswerFilter
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )
