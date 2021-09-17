from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.views.generic import DetailView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_session
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.filters import ImageFilterSet
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.cases.serializers import (
    HyperlinkedImageSerializer,
    RawImageFileSerializer,
    RawImageUploadSessionPatchSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.jqfileupload.models import StagedFile
from grandchallenge.reader_studies.tasks import (
    add_image_to_answer,
    add_images_to_reader_study,
)
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
    queryset = Image.objects.all().prefetch_related("files")
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
    queryset = RawImageUploadSession.objects.prefetch_related(
        "rawimagefile_set"
    ).all()
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return RawImageUploadSessionPatchSerializer
        else:
            return RawImageUploadSessionSerializer

    def validate_staged_files(self, *, staged_files):
        file_ids = [f.staged_file_id for f in staged_files]

        if any(f_id is None for f_id in file_ids):
            raise ValidationError("File has not been staged")

        chunks = StagedFile.objects.filter(file_id__in=file_ids)

        if len({c.client_filename for c in chunks}) != len(staged_files):
            raise ValidationError("Filenames must be unique")

        if (
            sum([f.end_byte - f.start_byte for f in chunks])
            > settings.UPLOAD_SESSION_MAX_BYTES
        ):
            raise ValidationError(
                "Total size of all files exceeds the upload limit"
            )

    @action(detail=True, methods=["patch"])
    def process_images(self, request, pk=None):
        upload_session: RawImageUploadSession = self.get_object()

        serializer = self.get_serializer(
            upload_session, data=request.data, partial=True
        )

        if serializer.is_valid():
            try:
                self.validate_staged_files(
                    staged_files=upload_session.rawimagefile_set.all()
                )
            except ValidationError as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

            if (
                upload_session.status == upload_session.PENDING
                and not upload_session.rawimagefile_set.filter(
                    consumed=True
                ).exists()
            ):
                upload_session.process_images(
                    linked_task=self.get_linked_task(
                        validated_data=serializer.validated_data
                    )
                )
                return Response(
                    "Image processing job queued.", status=status.HTTP_200_OK
                )
            else:
                return Response(
                    "Image processing job could not be queued.",
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

    def get_linked_task(self, *, validated_data):
        if "algorithm" in validated_data:
            return create_algorithm_jobs_for_session.signature(
                kwargs={
                    "algorithm_image_pk": validated_data[
                        "algorithm"
                    ].latest_ready_image.pk
                },
                immutable=True,
            )
        elif "archive" in validated_data:
            return add_images_to_archive.signature(
                kwargs={"archive_pk": validated_data["archive"].pk},
                immutable=True,
            )
        elif "reader_study" in validated_data:
            return add_images_to_reader_study.signature(
                kwargs={"reader_study_pk": validated_data["reader_study"].pk},
                immutable=True,
            )
        elif "answer" in validated_data:
            return add_image_to_answer.signature(
                kwargs={"answer_pk": validated_data["answer"].pk},
                immutable=True,
            )
        else:
            raise RuntimeError(
                "Algorithm image, archive or reader study must be set"
            )


class RawImageFileViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = RawImageFileSerializer
    queryset = RawImageFile.objects.all()
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]
