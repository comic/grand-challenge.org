from rest_framework import generics
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from comicmodels.models import ComicSite
from .models import Result, Submission, Job, Method
from .serializers import ResultSerializer, SubmissionSerializer, \
    JobSerializer, \
    MethodSerializer


class ResultList(generics.ListCreateAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class ResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer


class SubmissionList(generics.ListCreateAPIView):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user,
                        challenge=ComicSite.objects.get(
                            short_name=self.request.data.get('challenge')),
                        file=self.request.data.get('file'))


class JobList(generics.ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


class MethodList(generics.ListCreateAPIView):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
