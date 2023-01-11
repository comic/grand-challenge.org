from functools import reduce
from operator import or_

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import Http404, HttpResponse
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
from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
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
from grandchallenge.uploads.widgets import UserUploadMultipleWidget


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


class OSDImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Image
    permission_required = (
        f"{Image._meta.app_label}.view_{Image._meta.model_name}"
    )
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            dzi = self.object.files.get(image_type=ImageFile.IMAGE_TYPE_DZI)
        except ObjectDoesNotExist:
            raise Http404

        context.update({"dzi_url": dzi.file.url})

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


class VTKImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Image
    permission_required = (
        f"{Image._meta.app_label}.view_{Image._meta.model_name}"
    )
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "cases/image_detail_vtk.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.color_space != Image.COLOR_SPACE_GRAY:
            # vtk.js viewer fails to load color images
            raise Http404
        try:
            mh_file, _ = self.object.get_metaimage_files()
        except FileNotFoundError as e:
            raise Http404 from e

        context.update(
            {
                "mh_url": mh_file.file.url,
                "is_2d": self.object.depth in (None, 1),
            }
        )
        return context


class CSImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Image
    permission_required = (
        f"{Image._meta.app_label}.view_{Image._meta.model_name}"
    )
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "cases/image_detail_cs.html"

    def get_object(self):
        img = super().get_object()
        try:
            img.get_metaimage_files()
        except FileNotFoundError as e:
            raise Http404 from e

        if img.color_space not in (
            Image.COLOR_SPACE_GRAY,
            Image.COLOR_SPACE_RGBA,
            Image.COLOR_SPACE_RGB,
        ):
            # YCrBr not supported in cornerstone
            raise Http404

        return img


class ImageWidgetSelectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        query_params = request.GET.copy()
        interface = query_params.pop("interface", None)[0]
        widget_name = query_params.pop("WidgetChoice-" + interface, None)[0]
        help_text = query_params.pop("help_text", None)

        if widget_name == WidgetChoices.IMAGE_SEARCH.name:
            html_content = render_to_string(
                ImageSearchWidget.template_name,
                {
                    "widget": ImageSearchWidget().get_context(
                        name=interface,
                        value=None,
                        attrs={
                            "help_text": help_text[0] if help_text else None,
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
                                help_text[0] if help_text else None,
                                IMAGE_UPLOAD_HELP_TEXT,
                            ),
                        },
                    )["widget"],
                },
            )
            return HttpResponse(html_content)
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
        interface = request.GET.get("interface")
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


class CS3DImageDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Image
    permission_required = (
        f"{Image._meta.app_label}.view_{Image._meta.model_name}"
    )
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "cases/image_detail_cs3d.html"

    def get_object(self):
        img = super().get_object()
        try:
            img.get_metaimage_files()
        except FileNotFoundError as e:
            raise Http404 from e

        return img
