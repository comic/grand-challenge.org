import json
import uuid

from dal import autocomplete
from django.db.models import Q, TextChoices
from django.forms import Media
from django.http import JsonResponse
from django.views.generic import ListView, TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.algorithms.forms import NON_ALGORITHM_INTERFACES
from grandchallenge.api.permissions import IsAuthenticated
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
            object_slug = self.forwarded.pop("object")
            object = ReaderStudy.objects.get(slug=object_slug)
            qs = ComponentInterface.objects.exclude(
                slug__in=object.values_for_interfaces.keys()
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


class InterfaceProcessingMixin:
    def process_data_for_object(self, data):
        raise NotImplementedError

    def form_invalid(self, form):
        return JsonResponse(form.errors, status=400)

    def form_valid(self, form):
        self.process_data_for_object(form.cleaned_data)
        return JsonResponse({"redirect": self.get_success_url()})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "auto_id": f"id-{uuid.uuid4()}-%s",
                "base_obj": self.base_object,
            }
        )
        if self.request.method == "POST":
            data = json.load(self.request)
            for key, value in data.items():
                if (
                    key
                    in [
                        "order",
                        "csrfmiddlewaretoken",
                        "new_interfaces",
                        "help_text",
                        "current_value",
                        "interface_slug",
                    ]
                    or "WidgetChoice" in key
                    or "query" in key
                ):
                    continue
                interface = ComponentInterface.objects.get(slug=key)
                if interface.is_image_kind:
                    data[key] = value
            kwargs.update(
                {
                    "data": data,
                }
            )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        media = Media()
        for form_class in self.included_form_classes:
            for widget in form_class._possible_widgets:
                media = media + widget().media
        context.update(
            {
                "base_object": self.base_object,
                "form_media": media,
            }
        )
        return context
