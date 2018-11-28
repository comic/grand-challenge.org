from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from grandchallenge.challenges.models import Challenge
from grandchallenge.challenges.serializers import ChallengeSerializer


class ChallengeViewSet(ModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = (IsAuthenticated,)

#    def perform_create(self, serializer):
#        serializer.save(creator=self.request.user)

