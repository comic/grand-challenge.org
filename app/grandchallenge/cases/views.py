from django.conf import settings
from django.http import Http404
from django.views.generic import DetailView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
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
from rest_framework_csv.renderers import PaginatedCSVRenderer
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_session
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.cases.serializers import (
    HyperlinkedImageSerializer,
    RawImageFileSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyWithCustomPostPermissions,
)
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.reader_studies.tasks import add_images_to_reader_study


class RawImageUploadSessionDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = RawImageUploadSession
    permission_required = f"{RawImageUploadSession._meta.app_label}.view_{RawImageUploadSession._meta.model_name}"
    raise_exception = True


class ImageViewSet(ReadOnlyModelViewSet):
    serializer_class = HyperlinkedImageSerializer
    queryset = Image.objects.all().prefetch_related(
        "files",
        "archive_set",
        "componentinterfacevalue_set__algorithms_jobs_as_input",
    )
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (
        DjangoFilterBackend,
        ObjectPermissionsFilter,
    )
    filterset_fields = (
        "study",
        "origin",
        "archive",
    )
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )


def show_image(request, *, pk):
    from django.shortcuts import render

    try:
        image_file = ImageFile.objects.select_related("image").get(
            image=pk, image_type="DZI"
        )
    except Image.DoesNotExist:
        raise Http404("File not found.")

    return render(
        request,
        "cases/show_image.html",
        {"image_file": image_file, "url": image_file.file.url},
    )


class RawImageUploadSessionViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = RawImageUploadSessionSerializer
    queryset = RawImageUploadSession.objects.all()
    permission_classes = [DjangoObjectOnlyWithCustomPostPermissions]
    filter_backends = [ObjectPermissionsFilter]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def validate_staged_files(self):
        upload_session: RawImageUploadSession = self.get_object()

        file_ids = [
            f.staged_file_id for f in upload_session.rawimagefile_set.all()
        ]

        if any(f_id is None for f_id in file_ids):
            raise ValidationError("File has not been staged")

        files = [StagedAjaxFile(f_id) for f_id in file_ids]

        if not all(s.exists for s in files):
            raise ValidationError("File does not exist")

        if len({f.name for f in files}) != len(files):
            raise ValidationError("Filenames must be unique")

        if sum([f.size for f in files]) > settings.UPLOAD_SESSION_MAX_BYTES:
            raise ValidationError(
                "Total size of all files exceeds the upload limit"
            )

    @action(detail=True, methods=["patch"])
    def process_images(self, request, pk=None):
        upload_session: RawImageUploadSession = self.get_object()

        try:
            self.validate_staged_files()
        except ValidationError as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        if (
            upload_session.status == upload_session.PENDING
            and not upload_session.rawimagefile_set.filter(
                consumed=True
            ).exists()
        ):
            upload_session.process_images(linked_task=self._linked_task)
            return Response(
                "Image processing job queued.", status=status.HTTP_200_OK
            )
        else:
            return Response(
                "Image processing job could not be queued.",
                status=status.HTTP_400_BAD_REQUEST,
            )

    @property
    def _linked_task(self):
        upload_session = self.get_object()

        if upload_session.algorithm_image:
            return create_algorithm_jobs_for_session
        elif upload_session.archive:
            return add_images_to_archive
        elif upload_session.reader_study:
            return add_images_to_reader_study
        else:
            return None


class RawImageFileViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = RawImageFileSerializer
    queryset = RawImageFile.objects.all()
    permission_classes = [DjangoObjectOnlyWithCustomPostPermissions]
    filter_backends = [ObjectPermissionsFilter]
