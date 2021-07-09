from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from grandchallenge.timezones.serializers import TimezoneSerializer


class TimezoneAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def put(self, request, format=None):
        serializer = TimezoneSerializer(data=request.data)
        if serializer.is_valid():
            request.session["timezone"] = serializer.validated_data["timezone"]
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
