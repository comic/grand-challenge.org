from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.views.generic import DetailView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.filters import ImageFilterSet
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageUploadSession,
)
from grandchallenge.cases.serializers import (
    CSImageSerializer,
    HyperlinkedImageSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.subdomains.utils import reverse_lazy


class RawImageUploadSessionList(
    LoginRequiredMixin, PermissionListMixin, PaginatedTableListView,
):
    model = RawImageUploadSession
    permission_required = f"{RawImageUploadSession._meta.app_label}.view_{RawImageUploadSession._meta.model_name}"
    login_url = reverse_lazy("account_login")
    row_template = "cases/rawimageuploadsession_row.html"
    search_fields = [
        "pk",
    ]
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
    filter_backends = (
        DjangoFilterBackend,
        ObjectPermissionsFilter,
    )
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            self.object.get_metaimage_files()
        except FileNotFoundError as e:
            raise Http404 from e

        if self.object.depth > 1:
            # 3D volumes not supported in cornerstone
            raise Http404

        context.update({"image_pk": self.object.pk})
        return context


class CSImageLoader(RetrieveAPIView):
    queryset = Image.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (ObjectPermissionsFilter,)
    renderer_classes = (JSONRenderer,)
    serializer_class = CSImageSerializer
