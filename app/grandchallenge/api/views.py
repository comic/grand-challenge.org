from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ModelViewSet

from grandchallenge.api.serializers import SubmissionSerializer
from grandchallenge.challenges.models import Challenge
from grandchallenge.evaluation.models import Submission

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from rest_framework.authtoken.models import Token

from social_core.actions import do_complete
from social_django.utils import psa
from social_django.views import _do_login, NAMESPACE


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        # Validate that the challenge exists
        try:
            short_name = self.request.data.get("challenge")
            challenge = Challenge.objects.get(short_name=short_name)
        except Challenge.DoesNotExist:
            raise ValidationError(f"Challenge {short_name} does not exist.")

        serializer.save(
            creator=self.request.user,
            challenge=challenge,
            file=self.request.data.get("file"),
        )


# Used to forward the user after he is forwarded from OAUTH2 provider
@never_cache
@csrf_exempt
@psa('{0}:complete'.format(NAMESPACE))
def complete(request, backend, *args, **kwargs):
    """Authentication complete view"""
    result = do_complete(request.backend, _do_login, request.user,
                       redirect_name=REDIRECT_FIELD_NAME, request=request,
                       *args, **kwargs)

    token, created = Token.objects.get_or_create(user=request.user)
    return HttpResponseRedirect('http://test/%s' % token)
