from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.serializers import ChallengeSerializer


class ChallengeViewSet(ReadOnlyModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = (AllowAny,)
