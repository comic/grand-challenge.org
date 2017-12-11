from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from api.serializers import ResultSerializer, SubmissionSerializer, \
    JobSerializer, MethodSerializer
from comicmodels.models import ComicSite
from evaluation.models import Result, Submission, Job, Method


class ResultViewSet(ModelViewSet):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        # Validate that the challenge exists
        try:
            short_name = self.request.data.get('challenge')
            challenge = ComicSite.objects.get(
                short_name=short_name)
        except ComicSite.DoesNotExist:
            raise ValidationError(
                f"Challenge {short_name} does not exist.")

        serializer.save(creator=self.request.user,
                        challenge=challenge,
                        file=self.request.data.get('file'))


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class MethodViewSet(ModelViewSet):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)