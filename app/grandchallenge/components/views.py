import uuid

from dal import autocomplete
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, TextChoices
from django.forms import Media
from django.http import HttpResponse
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.views.generic import ListView, TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.algorithms.forms import NON_ALGORITHM_INTERFACES
from grandchallenge.api.permissions import IsAuthenticated
from grandchallenge.components.forms import NewFileUploadForm
from grandchallenge.components.models import ComponentInterface, InterfaceKind
from grandchallenge.components.serializers import ComponentInterfaceSerializer
from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


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


class InterfaceProcessingMixin(SuccessMessageMixin):
    def process_data_for_object(self, data):
        raise NotImplementedError

    def form_valid(self, form):
        form.instance = self.process_data_for_object(form.cleaned_data)
        response = super().form_valid(form)
        return HttpResponse(
            response.url,
            status=302,
            headers={
                "HX-Redirect": response.url,
                "HX-Refresh": True,
            },
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            instance = self.object
        else:
            instance = None
        kwargs.update(
            {
                "user": self.request.user,
                "auto_id": f"id-{uuid.uuid4()}",
                "base_obj": self.base_object,
                "instance": instance,
            }
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        media = Media()
        for form_class in self.included_form_classes:
            for widget in form_class._possible_widgets:
                media = media + widget().media
        if hasattr(self, "object"):
            object = self.object
        else:
            object = None
        context.update(
            {
                "base_object": self.base_object,
                "form_media": media,
                "object": object,
            }
        )
        return context

    def get_success_message(self, cleaned_data):
        return format_html(
            "{success_message} "
            "Image and file import jobs have been queued. "
            "You will be notified about errors related to image and file imports "
            "via a <a href={url}>notification</a>.",
            success_message=self.success_message,
            url=reverse("notifications:list"),
        )


class FileUpdateBaseView(ObjectPermissionRequiredMixin, TemplateView):
    form_class = NewFileUploadForm
    template_name = "components/object_files_update.html"
    raise_exception = True

    def get_permission_object(self):
        return self.base_object

    @cached_property
    def interface(self):
        return ComponentInterface.objects.get(
            slug=self.kwargs["interface_slug"]
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "form": self.form_class(
                    {"user": self.request.user, "interface": self.interface}
                ),
            }
        )
        return context
