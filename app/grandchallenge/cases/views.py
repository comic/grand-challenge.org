import json
from functools import reduce
from operator import or_

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from django.conf import settings
from django.db.models import Q
from django.forms import HiddenInput
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import DetailView, ListView
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from grandchallenge.cases.filters import ImageFilterSet
from grandchallenge.cases.forms import IMAGE_UPLOAD_HELP_TEXT
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.serializers import (
    HyperlinkedImageSerializer,
    RawImageUploadSessionSerializer,
)
from grandchallenge.cases.widgets import ImageSearchWidget, ImageWidgetChoices
from grandchallenge.components.form_fields import INTERFACE_FORM_FIELD_PREFIX
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
    get_object_if_allowed,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.subdomains.utils import reverse_lazy
from grandchallenge.uploads.models import UserUpload
from grandchallenge.uploads.widgets import UserUploadMultipleWidget
from grandchallenge.workstations.models import Workstation


class RawImageUploadSessionList(
    LoginRequiredMixin, ViewObjectPermissionListMixin, PaginatedTableListView
):
    model = RawImageUploadSession
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
    filter_backends = (DjangoFilterBackend, ViewObjectPermissionsFilter)
    filterset_class = ImageFilterSet
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    @action(detail=True)
    def health_imaging_signed_urls(self, request, pk=None):
        image = self.get_object()

        session = boto3.Session(
            region_name=settings.AWS_DEFAULT_REGION,
        )
        medical_imaging_auth = SigV4Auth(
            credentials=session.get_credentials(),
            service_name="medical-imaging",
            region_name=settings.AWS_DEFAULT_REGION,
        )

        image_set_url = f"https://runtime-medical-imaging.{settings.AWS_DEFAULT_REGION}.amazonaws.com/datastore/{settings.AWS_HEALTH_IMAGING_DATASTORE_ID}/imageSet/{image.dicom_image_set.image_set_id}"

        image_frame_requests = {}

        for frame_id in image.dicom_image_set.image_frame_ids:
            frame_request = AWSRequest(
                method="POST",
                url=f"{image_set_url}/getImageFrame",
                data=json.dumps({"imageFrameId": frame_id}),
            )
            medical_imaging_auth.add_auth(frame_request)

            image_frame_requests[frame_id] = {
                "url": frame_request.url,
                "method": frame_request.method,
                "data": frame_request.data,
                "headers": dict(frame_request.headers.items()),
            }

        metadata_request = AWSRequest(
            method="POST", url=f"{image_set_url}/getImageSetMetadata"
        )
        medical_imaging_auth.add_auth(metadata_request)

        return JsonResponse(
            {
                "get_image_set_metadata": {
                    "url": metadata_request.url,
                    "method": metadata_request.method,
                    "data": metadata_request.data,
                    "headers": dict(metadata_request.headers.items()),
                },
                "get_image_frames": image_frame_requests,
            }
        )


class RawImageUploadSessionViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    queryset = RawImageUploadSession.objects.all()
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ViewObjectPermissionsFilter]
    serializer_class = RawImageUploadSessionSerializer


class ImageWidgetSelectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        prefixed_interface_slug = self.request.GET.get(
            "prefixed-interface-slug"
        )
        get_object_or_404(
            ComponentInterface,
            slug=prefixed_interface_slug.replace(
                INTERFACE_FORM_FIELD_PREFIX, ""
            ),
        )
        widget_choice_name = request.GET.get(
            f"widget-choice-{prefixed_interface_slug}"
        )
        try:
            widget_choice = ImageWidgetChoices(widget_choice_name)
        except ValueError:
            raise Http404(f"Widget choice {widget_choice_name} not found")

        if widget_choice == ImageWidgetChoices.IMAGE_SEARCH:
            return HttpResponse(
                ImageSearchWidget().render(
                    name=prefixed_interface_slug,
                    value=None,
                )
            )
        elif widget_choice == ImageWidgetChoices.IMAGE_UPLOAD:
            return HttpResponse(
                UserUploadMultipleWidget().render(
                    name=prefixed_interface_slug,
                    value=None,
                    attrs={
                        "id": prefixed_interface_slug,
                        "help_text": IMAGE_UPLOAD_HELP_TEXT,
                    },
                )
            )
        elif widget_choice == ImageWidgetChoices.IMAGE_SELECTED and (
            current_value_list := request.GET.getlist("current-value-pk")
        ):
            # this can happen on the display set update view or redisplay of
            # form upon validation, where one of the options is the current
            # image, this enables switching back from one of the above widgets
            # to the chosen image. This makes sure the form element with the
            # right name is available on resubmission.
            image = get_object_if_allowed(
                model=Image,
                pk=current_value_list[0],
                user=request.user,
                codename="view_image",
            )
            if image:
                return HttpResponse(
                    HiddenInput().render(
                        name=prefixed_interface_slug,
                        value=image.pk,
                    )
                )
            hidden_inputs_for_uploads = [
                HiddenInput().render(
                    name=prefixed_interface_slug,
                    value=pk,
                )
                for pk in current_value_list
                if get_object_if_allowed(
                    model=UserUpload,
                    pk=pk,
                    user=request.user,
                    codename="change_userupload",
                )
            ]
            if hidden_inputs_for_uploads:
                return HttpResponse(hidden_inputs_for_uploads)
            raise Http404(f"Selected image {current_value_list} not found")
        elif widget_choice == ImageWidgetChoices.UNDEFINED:
            # this happens when switching back from one of the
            # above widgets to the "Choose data source" option
            return HttpResponse()
        raise NotImplementedError(
            f"Response for widget choice {widget_choice} not implemented"
        )


class ImageSearchResultView(
    LoginRequiredMixin, ViewObjectPermissionListMixin, ListView
):
    template_name = "cases/image_search_result_select.html"
    search_fields = ["pk", "name"]
    model = Image
    paginate_by = 50

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        prefixed_interface_slug = request.GET.get("prefixed-interface-slug")
        query = request.GET.get("query-" + prefixed_interface_slug)
        if query:
            q = reduce(
                or_,
                [Q(**{f"{f}__icontains": query}) for f in self.search_fields],
                Q(),
            )
            qs = qs.filter(q).order_by("name")
        self.object_list = qs
        return self.render_to_response(self.get_context_data(**kwargs))
