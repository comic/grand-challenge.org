from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from comicmodels.models import ComicSite
from evaluation.models import Result, Submission, Job, Method
from evaluation.serializers import ResultSerializer, SubmissionSerializer, \
    JobSerializer, MethodSerializer


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
        serializer.save(user=self.request.user,
                        challenge=ComicSite.objects.get(
                            short_name=self.request.data.get('challenge')),
                        file=self.request.data.get('file'))


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class MethodViewSet(ModelViewSet):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
