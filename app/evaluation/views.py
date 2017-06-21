from .models import Result
from .serializers import ResultSerializer
from rest_framework import generics

class ResultList(generics.ListCreateAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer

class ResultDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Result.objects.all()
    serializer_class = ResultSerializer
