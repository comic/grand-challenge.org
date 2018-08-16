from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet

from grandchallenge.api.serializers import (
    ResultSerializer, SubmissionSerializer, JobSerializer, MethodSerializer
)
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Result, Submission, Job, Method


class ResultViewSet(ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        # Validate that the challenge exists
        try:
            short_name = self.request.data.get('challenge')
            challenge = Challenge.objects.get(short_name=short_name)
        except Challenge.DoesNotExist:
            raise ValidationError(f"Challenge {short_name} does not exist.")

        serializer.save(
            creator=self.request.user,
            challenge=challenge,
            file=self.request.data.get('file'),
        )


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


class MethodViewSet(ModelViewSet):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
