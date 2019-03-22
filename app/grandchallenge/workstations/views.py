from rest_framework.permissions import IsAdminUser
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.viewsets import ModelViewSet

from grandchallenge.workstations.forms import WorkstationForm
from grandchallenge.workstations.models import Workstation
from grandchallenge.workstations.serializers import WorkstationSerializer


class FormTemplateHTMLRenderer(TemplateHTMLRenderer):
    def get_template_context(self, data, renderer_context):
        context = super().get_template_context(
            data=data, renderer_context=renderer_context
        )
        form = renderer_context["form_class"]

        try:
            context.update({"form": form})
        except AttributeError:
            # The context is not a dictionary, a list instead. This happens
            # if no pagination class is used.
            context = {"results": context, "form": form}

        return context


class WorkstationsViewSet(ModelViewSet):
    queryset = Workstation.objects.all()
    serializer_class = WorkstationSerializer
    form_class = WorkstationForm
    permission_classes = (IsAdminUser,)
    template_name = "workstations/workstation_list.html"
    renderer_classes = (JSONRenderer, FormTemplateHTMLRenderer)

    def get_renderer_context(self):
        # TODO: Make this a mixin and make sure that the form_class is set
        context = super().get_renderer_context()
        context.update({"form_class": self.form_class})
        return context
