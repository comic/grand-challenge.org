from rest_framework import generics

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


class JobList(generics.ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


class MethodList(generics.ListCreateAPIView):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer
