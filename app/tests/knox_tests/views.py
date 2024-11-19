from knox.auth import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from grandchallenge.api.permissions import IsAuthenticated


class RootView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response("api root")
