from functools import reduce
from operator import or_

from django.conf import settings
from django.db.models import Q
from django.forms import HiddenInput
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import DetailView, ListView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.filters import ImageFilterSet
from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.serializers import (
    HyperlinkedImageSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.cases.widgets import ImageSearchWidget, WidgetChoices
from grandchallenge.components.form_fields import _join_with_br
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
    get_objects_for_user,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadMultipleWidget
from grandchallenge.workstations.models import Workstation


class RawImageUploadSessionList(
    LoginRequiredMixin, PermissionListMixin, PaginatedTableListView
):
    model = RawImageUploadSession
    permission_required = f"{RawImageUploadSession._meta.app_label}.view_{RawImageUploadSession._meta.model_name}"
    login_url = reverse_lazy("account_login")
    row_template = "cases/rawimageuploadsession_row.html"
    search_fields = ["pk"]
    columns = [
        Column(title="ID", sort_field="pk"),
        Column(title="Created", sort_field="created"),
        Column(title="Status", sort_field="status"),
        Column(title="Error Message", sort_field="error_message"),
    ]
    default_sort_column = 1


class RawImageUploadSessionDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = RawImageUploadSession
    permission_required = f"{RawImageUploadSession._meta.app_label}.view_{RawImageUploadSession._meta.model_name}"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(
            {
                "workstation": Workstation.objects.filter(
                    slug=settings.DEFAULT_WORKSTATION_SLUG
                ).get()
            }
        )
        return context


class ImageViewSet(ReadOnlyModelViewSet):
    serializer_class = HyperlinkedImageSerializer
    queryset = (
        Image.objects.all()
        .prefetch_related("files")
        .select_related("modality")
    )
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (DjangoFilterBackend, ObjectPermissionsFilter)
    filterset_class = ImageFilterSet
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )


class RawImageUploadSessionViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = RawImageUploadSession.objects.all()
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]
    serializer_class = RawImageUploadSessionSerializer


class ImageWidgetSelectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        interface = request.GET.get("interface_slug")
        widget_name = request.GET.get(f"WidgetChoice-{interface}")
        help_text = request.GET.get("help_text")
        current_value = request.GET.get("current_value")

        if widget_name == WidgetChoices.IMAGE_SEARCH.name:
            html_content = render_to_string(
                ImageSearchWidget.template_name,
                {
                    "widget": ImageSearchWidget().get_context(
                        name=interface,
                        value=None,
                        attrs={
                            "help_text": help_text if help_text else None,
                        },
                    )["widget"],
                },
            )
            return HttpResponse(html_content)
        elif widget_name == WidgetChoices.IMAGE_UPLOAD.name:
            html_content = render_to_string(
                UserUploadMultipleWidget.template_name,
                {
                    "widget": UserUploadMultipleWidget().get_context(
                        name=interface,
                        value=None,
                        attrs={
                            "id": interface,
                            "help_text": _join_with_br(
                                help_text if help_text else None,
                                IMAGE_UPLOAD_HELP_TEXT,
                            ),
                        },
                    )["widget"],
                },
            )
            return HttpResponse(html_content)
        elif current_value and (
            Image.objects.filter(pk=current_value).exists()
            or UserUpload.objects.filter(pk=current_value).exists()
        ):
            # this can happen on the display set update view or redisplay of
            # form upon validation, where one of the options is the current
            # image, this enables switching back from one of the above widgets
            # to the chosen image. In the case of form redisplay on validation
            # error, current_value will be set in the flexible image widget
            # select dropdown element with name starting with "WidgetChoice-"
            # which will not be captured on resubmission, because the
            # current_value is looked up from the form data element with
            # interface name (in JobCreateForm and MultipleCIVForm). This make
            # sure the form element with the right name is available on
            # resubmission.
            html_content = render_to_string(
                HiddenInput.template_name,
                {
                    "widget": {
                        "name": interface,
                        "value": current_value,
                        "type": "hidden",
                    },
                },
            )
            return HttpResponse(html_content)
        elif widget_name == WidgetChoices.UNDEFINED.name:
            # this happens when switching back from one of the
            # above widgets to the "Choose data source" option
            return HttpResponse()
        else:
            raise RuntimeError("Unknown widget type")


class ImageSearchView(LoginRequiredMixin, ListView):
    template_name = "cases/image_search_result_select.html"
    search_fields = ["pk", "name"]
    model = Image
    paginate_by = 50

    def get_queryset(self):
        return get_objects_for_user(self.request.user, "cases.view_image")

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        interface = request.GET.get("interface_slug")
        query = request.GET.get("query-" + interface)
        if query:
            q = reduce(
                or_,
                [Q(**{f"{f}__icontains": query}) for f in self.search_fields],
                Q(),
            )
            qs = qs.filter(q).order_by("name")
        self.object_list = qs
        context = self.get_context_data(**kwargs)
        context["interface"] = interface
        return TemplateResponse(
            request=request,
            template=self.template_name,
            context=context,
        )
