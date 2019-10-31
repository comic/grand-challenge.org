from django.http import Http404
from django.views.generic import CreateView, DetailView
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import (
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
    UploadSessionState,
)
from grandchallenge.cases.serializers import (
    ImageSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class UploadRawFiles(UserIsStaffMixin, CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class ShowUploadSessionState(UserIsStaffMixin, DetailView):
    model = RawImageUploadSession

    def get_context_data(self, **kwargs):
        result = super().get_context_data(**kwargs)
        result["upload_session"] = result["object"]
        result["raw_files"] = RawImageFile.objects.filter(
            upload_session=result["object"]
        ).all()
        result["images"] = Image.objects.filter(origin=result["object"]).all()
        result["process_finished"] = (
            result["object"].session_state == UploadSessionState.stopped
        )
        return result


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

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
