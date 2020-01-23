from django.contrib.auth.models import User, Group
from django.http import HttpResponseRedirect
from django_filters import rest_framework as filters
from rest_framework import mixins, exceptions
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from comic.eyra.models import Algorithm, Job, Benchmark, Submission, DataFile, DataSet
from comic.eyra.permissions import EyraPermissions
from comic.eyra.serializers import AlgorithmSerializer, JobSerializer, BenchmarkSerializer, SubmissionSerializer, \
    DataFileSerializer, DataSetSerializer, RegisterSerializer, UserSerializer, GroupSerializer


class AlgorithmFilter(filters.FilterSet):
    has_admin = filters.NumberFilter(method='has_admin_filter')

    class Meta:
        model = Algorithm
        fields = ['creator', 'has_admin']

    def has_admin_filter(self, queryset, name, value):
        return queryset.filter(admin_group__user__id__contains=value)


class AlgorithmViewSet(ModelViewSet):
    # queryset = Algorithm.objects.exclude(output_type__name__exact='OutputMetrics')
    queryset = Algorithm.objects.all()
    serializer_class = AlgorithmSerializer
    permission_classes = (EyraPermissions,)
    filterset_class = AlgorithmFilter

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class JobViewSet(ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = (EyraPermissions,)



####



class BenchmarkFilter(filters.FilterSet):
    has_admin = filters.NumberFilter(method='has_admin_filter')

    class Meta:
        model = Benchmark
        fields = ['creator', 'has_admin']

    def has_admin_filter(self, queryset, name, value):
        return queryset.filter(admin_group__user__id__contains=value)


class BenchmarkViewSet(ModelViewSet):
    queryset = Benchmark.objects.all()
    serializer_class = BenchmarkSerializer
    permission_classes = (EyraPermissions,)
    filterset_class = BenchmarkFilter

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = (EyraPermissions,)
    # filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ['benchmark', 'creator', 'is_private']

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)

####

class DataFileViewSet(ModelViewSet):
    queryset = DataFile.objects.all()
    serializer_class = DataFileSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        if self.action == "list":
            # return DataSet.objects.filter(frozen=True)
            return DataFile.objects.all()
        return DataFile.objects.all()

    @action(detail=True)
    def download(self, request, *args, **kwargs):
        data_file = DataFile.objects.get(pk=kwargs['pk'])
        return HttpResponseRedirect(data_file.get_download_url())


class DataSetViewSet(ModelViewSet):
    queryset = DataSet.objects.all()
    serializer_class = DataSetSerializer
    permission_classes = (EyraPermissions,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


####


class RegisterViewSet(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)


class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        user = User.objects.get(email=request.data.get('email'))
        if user.check_password(request.data.get('password')):
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': str(token)
            })
        else:
            raise exceptions.AuthenticationFailed


class UserViewSet(ModelViewSet):
    queryset = User.objects.all() # filter(~Q(username="AnonymousUser"))
    serializer_class = UserSerializer
    permission_classes = (EyraPermissions,)


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (EyraPermissions,)
