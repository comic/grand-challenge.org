from django.db.models import TextChoices
from django.views.generic import ListView, TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.algorithms.forms import NON_ALGORITHM_INTERFACES
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.serializers import ComponentInterfaceSerializer


class ComponentInterfaceViewSet(ReadOnlyModelViewSet):
    serializer_class = ComponentInterfaceSerializer
    queryset = ComponentInterface.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ("slug",)
    filter_backends = (DjangoFilterBackend,)


class ComponentInterfaceIOSwitch(LoginRequiredMixin, TemplateView):
    template_name = "components/componentinterface_io_switch.html"


class InterfaceListTypeOptions(TextChoices):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    ITEM = "ITEM"
    CASE = "CASE"


class InterfaceObjectTypeOptions(TextChoices):
    ALGORITHM = "ALGORITHM"
    ARCHIVE = "ARCHIVE"
    READER_STUDY = "READER STUDY"


class ComponentInterfaceList(LoginRequiredMixin, ListView):
    model = ComponentInterface
    queryset = ComponentInterface.objects.exclude(
        slug__in=NON_ALGORITHM_INTERFACES
    )
    list_type = None
    object_type = None

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "list_type": self.list_type,
                "object_type": self.object_type,
                "list_type_options": InterfaceListTypeOptions,
                "object_type_options": InterfaceObjectTypeOptions,
            }
        )
        return context
