from django.contrib import messages
from django.http import Http404
from django.views.generic import DetailView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.cases.serializers import (
    ImageSerializer,
    RawImageFileSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyWithCustomPostPermissions,
)


class RawImageUploadSessionDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = RawImageUploadSession
    permission_required = f"{RawImageUploadSession._meta.app_label}.view_{RawImageUploadSession._meta.model_name}"
    raise_exception = True


class ImageViewSet(ReadOnlyModelViewSet):
    serializer_class = ImageSerializer
    queryset = Image.objects.all()
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ObjectPermissionsFilter]

    def get_queryset(self):
        filters = {
            "worklist": self.request.query_params.get("worklist", None),
            "study": self.request.query_params.get("study", None),
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        queryset = super().get_queryset().filter(**filters)

        return queryset


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

    @action(detail=True, methods=["patch"])
    def process_images(self, request, pk=None):
        upload_session: RawImageUploadSession = self.get_object()
        if (
            upload_session.status == upload_session.PENDING
            and not upload_session.rawimagefile_set.filter(
                consumed=True
            ).exists()
        ):
            upload_session.process_images()
            messages.add_message(
                request, messages.SUCCESS, "Image processing job queued."
            )
            return Response(status=status.HTTP_200_OK)
        else:
            messages.add_message(
                request,
                messages.ERROR,
                "Image processing job could not be queued.",
            )
            return Response(status=status.HTTP_400_BAD_REQUEST)


class RawImageFileViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = RawImageFileSerializer
    queryset = RawImageFile.objects.all()
    permission_classes = [DjangoObjectOnlyWithCustomPostPermissions]
    filter_backends = [ObjectPermissionsFilter]
