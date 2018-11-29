from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.serializers import ChallengeSerializer


class ChallengeAccessPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == "GET":
            # List
            return True
        elif request.method == "POST":
            # Create: only authenticated users
            return request.user and request.user.is_authenticated
        elif request.method == "PUT":
            # Update: only authenticated users (object permission is checked next)
            return request.user and request.user.is_authenticated
        return False

    def has_object_permission(self, request, view, challenge):
        if request.method == "PUT":
            # Update: only challenge admins
            return challenge.is_admin(request.user)
        return True


class ChallengeViewSet(ModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = (ChallengeAccessPermission,)

    def perform_create(self, serializer):
        # Add the logged in user as the challenge creator
        serializer.save(creator=self.request.user)
