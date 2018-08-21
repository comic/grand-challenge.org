from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet

from grandchallenge.api.serializers import SubmissionSerializer
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Submission


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        # Validate that the challenge exists
        try:
            short_name = self.request.data.get('challenge')
            challenge = Challenge.objects.get(short_name=short_name)
        except Challenge.DoesNotExist:
            raise ValidationError(f"Challenge {short_name} does not exist.")

        serializer.save(
            creator=self.request.user,
            challenge=challenge,
            file=self.request.data.get('file'),
        )
