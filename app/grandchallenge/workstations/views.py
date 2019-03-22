from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer

from grandchallenge.workstations.models import Workstation
from grandchallenge.workstations.serializers import WorkstationSerializer


class WorkstationsList(ListAPIView):
    queryset = Workstation.objects.all()
    serializer_class = WorkstationSerializer
    permission_classes = (IsAdminUser,)
    template_name = "workstations/workstation_list.html"
    renderer_classes = (JSONRenderer, TemplateHTMLRenderer)
