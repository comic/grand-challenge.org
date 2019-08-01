from django.contrib.auth.models import User, Group

from rest_framework import mixins, exceptions
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from comic.eyra_users.permissions import EyraPermissions
from comic.eyra_users.serializers import UserSerializer, GroupSerializer, RegisterSerializer


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
