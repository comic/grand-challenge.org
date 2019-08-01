from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from comic.eyra_users.serializers import (
    UserSerializer,
    GroupSerializer,
)

from django.contrib.auth import REDIRECT_FIELD_NAME, logout
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from rest_framework.authtoken.models import Token

from social_core.actions import do_complete, do_auth
from social_django.utils import psa
from social_django.views import _do_login


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# The social_django app works with only one URL namespace, and only one LOGIN_REDIRECT_URL.
# As the REST API needs its own namespace and redirect, the social_django.views.complete and social_django.views.auth
# views are reimplemented here specifically for authentication through the REST API.

# The namespace used for the REST API social authentication
NAMESPACE = "api:social"

# Used to forward the user after he is forwarded from OAUTH2 provider
@never_cache
@csrf_exempt
@psa("{0}:complete".format(NAMESPACE))
def rest_api_complete(request, backend, *args, **kwargs):
    """Authentication complete view"""
    # The social_django do_complete function returns settings.LOGIN_REDIRECT_URL if no next
    # parameter is given. For the API, a different default redirect_url is needed, but
    # social_django only allows a single default. Also, the token should be added to the
    # redirect url.
    redirect_url = request.session.get("next", "/")

    result = do_complete(
        request.backend,
        _do_login,
        request.user,
        redirect_name=REDIRECT_FIELD_NAME,
        request=request,
        *args,
        **kwargs,
    )

    token, created = Token.objects.get_or_create(user=request.user)

    # For the API, the session is not needed: the token is all that is needed.
    logout(request)

    return HttpResponseRedirect(redirect_url + "?token={}".format(token))


# This function is not different from social_django.views.auth, but is repeated here so it includes the proper namespace.
@never_cache
@psa("{0}:complete".format(NAMESPACE))
def rest_api_auth(request, backend):
    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)
