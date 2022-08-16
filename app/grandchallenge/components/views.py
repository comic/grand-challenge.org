from dal import autocomplete
from django.db.models import Q, TextChoices
from django.views.generic import ListView, TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.algorithms.forms import NON_ALGORITHM_INTERFACES
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.reader_studies.models import ReaderStudy


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


class ComponentInterfaceAutocomplete(
    LoginRequiredMixin, autocomplete.Select2QuerySetView
):
    def get_queryset(self):
        if self.forwarded:
            reader_study_slug = self.forwarded.pop("reader-study")
            reader_study = ReaderStudy.objects.get(slug=reader_study_slug)
            qs = ComponentInterface.objects.exclude(
                slug__in=reader_study.values_for_interfaces.keys()
            ).exclude(pk__in=self.forwarded.values())
        else:
            qs = ComponentInterface.objects.filter(
                kind__in=InterfaceKind.interface_type_image()
            ).order_by("title")

        if self.q:
            qs = qs.filter(
                Q(title__icontains=self.q)
                | Q(slug__icontains=self.q)
                | Q(description__icontains=self.q)
            )

        return qs

    def get_result_label(self, result):
        return result.title
