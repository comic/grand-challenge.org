from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import LoginRequiredMixin
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.archives.filters import ArchiveFilter
from grandchallenge.archives.forms import (
    AddCasesForm,
    ArchiveForm,
    ArchiveItemForm,
    ArchiveItemsToReaderStudyForm,
    ArchivePermissionRequestUpdateForm,
    UploadersForm,
    UsersForm,
)
from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)
from grandchallenge.archives.serializers import (
    ArchiveItemPostSerializer,
    ArchiveItemSerializer,
    ArchiveSerializer,
)
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.forms import MultipleCIVForm
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.views import (
    CIVSetCreateMixin,
    InterfacesCreateBaseView,
    MultipleCIVProcessingBaseView,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.models import DisplaySet, ReaderStudy
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class ArchiveList(FilterMixin, PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
    queryset = Archive.objects.prefetch_related("optional_hanging_protocols")
    ordering = "-created"
    filter_class = ArchiveFilter
    paginate_by = 40

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update(
            {
                "jumbotron_title": "Archives",
                "jumbotron_description": format_html(
                    (
                        "An archive can be used to collect set of medical "
                        "images, which can later be used in a reader study, "
                        "challenge or algorithm. Please <a href='{}'>contact "
                        "us</a> if you would like to set up your own archive."
                    ),
                    mark_safe(
                        random_encode("mailto:support@grand-challenge.org")
                    ),
                ),
            }
        )

        return context


class ArchiveCreate(PermissionRequiredMixin, UserFormKwargsMixin, CreateView):
    model = Archive
    form_class = ArchiveForm
    permission_required = (
        f"{model._meta.app_label}.add_{model._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response


class ArchiveDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.use_{model._meta.model_name}"
    )
    raise_exception = True
    queryset = Archive.objects.prefetch_related("optional_hanging_protocols")

    def on_permission_check_fail(self, request, response, obj=None):
        response = self.get(request)
        return response

    def check_permissions(self, request):
        try:
            return super().check_permissions(request)
        except PermissionDenied:
            return HttpResponseRedirect(
                reverse(
                    "archives:permission-request-create",
                    kwargs={"slug": self.object.slug},
                )
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_remove_form = UsersForm()
        user_remove_form.fields["action"].initial = UsersForm.REMOVE

        uploader_remove_form = UploadersForm()
        uploader_remove_form.fields["action"].initial = UploadersForm.REMOVE

        editor_remove_form = EditorsForm()
        editor_remove_form.fields["action"].initial = EditorsForm.REMOVE

        limit = 1000

        context.update(
            {
                "user_remove_form": user_remove_form,
                "uploader_remove_form": uploader_remove_form,
                "editor_remove_form": editor_remove_form,
                "now": now().isoformat(),
                "limit": limit,
                "offsets": range(
                    0,
                    Image.objects.filter(
                        componentinterfacevalue__archive_items__archive=context[
                            "object"
                        ]
                    ).count(),
                    limit,
                ),
            }
        )

        pending_permission_requests = ArchivePermissionRequest.objects.filter(
            archive=context["object"], status=ArchivePermissionRequest.PENDING
        ).count()
        context.update(
            {"pending_permission_requests": pending_permission_requests}
        )

        return context


class ArchiveUpdate(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Archive
    form_class = ArchiveForm
    permission_required = (
        f"{model._meta.app_label}.change_{model._meta.model_name}"
    )
    raise_exception = True


class ArchiveGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "archives/archive_user_groups_form.html"
    permission_required = (
        f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
    )

    @property
    def obj(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])


class ArchiveEditorsUpdate(ArchiveGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#editors"


class ArchiveUploadersUpdate(ArchiveGroupUpdateMixin):
    form_class = UploadersForm
    success_message = "Uploaders successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#uploaders"


class ArchiveUsersUpdate(ArchiveGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#users"


class ArchivePermissionRequestCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = ArchivePermissionRequest
    fields = ()

    @property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_success_url(self):
        return self.archive.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.archive = self.archive
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form.add_error(None, ErrorList(e.messages))
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permission_request = ArchivePermissionRequest.objects.filter(
            archive=self.archive, user=self.request.user
        ).first()
        context.update(
            {"permission_request": permission_request, "archive": self.archive}
        )
        return context


class ArchivePermissionRequestList(ObjectPermissionRequiredMixin, ListView):
    model = ArchivePermissionRequest
    permission_required = (
        f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
    )
    raise_exception = True

    @property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(archive=self.archive)
            .exclude(status=ArchivePermissionRequest.ACCEPTED)
            .select_related("user__user_profile", "user__verification")
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context


class ArchivePermissionRequestUpdate(PermissionRequestUpdate):
    model = ArchivePermissionRequest
    form_class = ArchivePermissionRequestUpdateForm
    base_model = Archive
    redirect_namespace = "archives"
    user_check_attrs = ["is_user", "is_uploader", "is_editor"]
    permission_required = (
        f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.base_object})
        return context


class ArchiveUploadSessionCreate(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = RawImageUploadSession
    form_class = AddCasesForm
    template_name = "archives/archive_upload_session_create.html"
    permission_required = (
        f"{Archive._meta.app_label}.upload_{Archive._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "linked_task": add_images_to_archive.signature(
                    kwargs={"archive_pk": self.archive.pk}, immutable=True
                ),
                "interface_viewname": "components:component-interface-list-archives",
            }
        )
        return kwargs

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context


class ArchiveEditArchiveItem(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    FormView,
):
    form_class = ArchiveItemForm
    template_name = "archives/archive_item_form.html"
    permission_required = (
        f"{ArchiveItem._meta.app_label}.change_{ArchiveItem._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.archive_item

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["archive_slug"])

    @cached_property
    def archive_item(self):
        return get_object_or_404(ArchiveItem, pk=self.kwargs["pk"])

    @cached_property
    def interface(self):
        return get_object_or_404(
            ComponentInterface, slug=self.kwargs["interface_slug"]
        )

    def get_success_url(self):
        return reverse(
            "archives:items-list", kwargs={"slug": self.archive.slug}
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"archive_item": self.archive_item, "interface": self.interface}
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"archive": self.archive})
        return context

    def form_valid(self, form):
        for ci_slug, value in form.cleaned_data.items():
            self.archive_item.create_civ(
                ci_slug=ci_slug, new_value=value, user=self.request.user
            )
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Archive item will be updated. It may take some time for your "
            "changes to become visible.",
        )
        return HttpResponseRedirect(self.get_success_url())


class ArchiveItemsList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView
):
    model = ArchiveItem
    permission_required = (
        f"{Archive._meta.app_label}.use_{Archive._meta.model_name}"
    )
    raise_exception = True
    template_name = "archives/archive_items_list.html"
    row_template = "archives/archive_items_row.html"
    search_fields = [
        "pk",
        "values__interface__title",
        "values__value",
        "values__image__name",
        "values__file",
    ]
    columns = [
        Column(title="Values", sort_field="created"),
        Column(title="Add"),
        Column(title="View"),
    ]

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "archive": self.archive,
                "interfaces": ComponentInterface.objects.all().order_by(
                    "title"
                ),
            }
        )
        return context

    def render_row(self, *, object_, page_context):
        page_context["object_interfaces"] = [
            v.interface for v in object_.values.all()
        ]
        return super().render_row(object_=object_, page_context=page_context)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(archive=self.archive).prefetch_related("values")


class ArchiveCasesList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView
):
    model = Image
    permission_required = (
        f"{Archive._meta.app_label}.use_{Archive._meta.model_name}"
    )
    raise_exception = True
    template_name = "archives/archive_cases_list.html"
    row_template = "archives/archive_cases_row.html"
    search_fields = [
        "pk",
        "name",
        "patient_id",
        "patient_name",
        "patient_birth_date",
        "patient_age",
        "patient_sex",
        "study_date",
        "study_instance_uid",
        "series_instance_uid",
        "study_description",
        "series_description",
    ]
    columns = [
        Column(title="Name", sort_field="name"),
        Column(title="Created", sort_field="created"),
        Column(title="Creator", sort_field="origin__creator__username"),
        Column(
            title="Patient ID",
            sort_field="patient_id",
            optional_condition=lambda o: o.patient_id,
        ),
        Column(
            title="Patient name",
            sort_field="patient_name",
            optional_condition=lambda o: o.patient_name,
        ),
        Column(
            title="Patient birth date",
            sort_field="patient_birth_date",
            optional_condition=lambda o: o.patient_birth_date,
        ),
        Column(
            title="Patient age",
            sort_field="patient_age",
            optional_condition=lambda o: o.patient_age,
        ),
        Column(
            title="Patient sex",
            sort_field="patient_sex",
            optional_condition=lambda o: o.patient_sex,
        ),
        Column(
            title="Study Instance UID",
            sort_field="study_instance_uid",
            optional_condition=lambda o: o.study_instance_uid,
        ),
        Column(
            title="Study description",
            sort_field="study_description",
            optional_condition=lambda o: o.study_description,
        ),
        Column(
            title="Study date",
            sort_field="study_date",
            optional_condition=lambda o: o.study_date,
        ),
        Column(
            title="Series Instance UID",
            sort_field="series_instance_uid",
            optional_condition=lambda o: o.series_instance_uid,
        ),
        Column(
            title="Series description",
            sort_field="series_description",
            optional_condition=lambda o: o.series_description,
        ),
        Column(title="View"),
        Column(
            title="Algorithm Results",
            sort_field="pk",
            optional_condition=lambda o: any(
                civ.algorithms_jobs_as_input.exists()
                for civ in o.componentinterfacevalue_set.all()
            ),
        ),
        Column(title="Download"),
    ]

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs.filter(
                componentinterfacevalue__archive_items__archive=self.archive
            )
            .prefetch_related(
                "files",
                "componentinterfacevalue_set__algorithms_jobs_as_input__algorithm_image__algorithm",
            )
            .select_related(
                "origin__creator__user_profile",
                "origin__creator__verification",
            )
        )


class ArchiveItemsToReaderStudyUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = ArchiveItemsToReaderStudyForm
    permission_required = (
        f"{Archive._meta.app_label}.use_{Archive._meta.model_name}"
    )
    raise_exception = True
    template_name = "archives/archive_cases_to_reader_study_form.html"

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "archive": self.archive})
        return kwargs

    def form_valid(self, form):
        reader_study: ReaderStudy = form.cleaned_data["reader_study"]
        items = form.cleaned_data["items"]

        for item in items:
            values = item.values.all()
            ds = DisplaySet.objects.create(reader_study=reader_study)
            ds.values.set(values)

        self.success_url = reader_study.get_absolute_url()
        self.success_message = f"Added {len(items)} cases to {reader_study}."

        return super().form_valid(form)


class ArchiveViewSet(ReadOnlyModelViewSet):
    serializer_class = ArchiveSerializer
    queryset = Archive.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (DjangoFilterBackend, ObjectPermissionsFilter)
    filterset_fields = ("slug",)
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    @action(detail=True)
    def patients(self, request, pk=None):
        archive = self.get_object()
        patients = (
            Image.objects.filter(
                componentinterfacevalue__archive_items__archive=archive
            )
            .order_by("patient_id")
            .values_list("patient_id", flat=True)
            .distinct("patient_id")
        )
        return Response(patients)

    @action(detail=True)
    def studies(self, request, pk=None):
        try:
            patient_id = self.request.query_params["patient_id"]
        except MultiValueDictKeyError:
            raise Http404
        archive = self.get_object()
        studies = (
            Image.objects.filter(
                componentinterfacevalue__archive_items__archive=archive,
                patient_id=patient_id,
            )
            .order_by("study_description")
            .values_list("study_description", flat=True)
            .distinct("study_description")
        )
        return Response(studies)


class ArchiveItemViewSet(
    CreateModelMixin, UpdateModelMixin, ReadOnlyModelViewSet
):
    queryset = ArchiveItem.objects.all().prefetch_related(
        "archive__hanging_protocol",
        "archive__optional_hanging_protocols",
    )
    serializer_class = ArchiveItemSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["archive"]

    def get_serializer_class(self):
        if "update" in self.action or "create" in self.action:
            return ArchiveItemPostSerializer
        else:
            return ArchiveItemSerializer


class ArchiveItemCreateView(
    CIVSetCreateMixin,
    MultipleCIVProcessingBaseView,
):
    form_class = MultipleCIVForm
    permission_required = (
        f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
    )
    included_form_classes = (
        MultipleCIVForm,
        *MultipleCIVProcessingBaseView.included_form_classes,
    )
    success_message = "Archive item has been created."
    model_to_add = ArchiveItem

    def get_permission_object(self):
        return self.base_object

    @property
    def base_object(self):
        return Archive.objects.get(slug=self.kwargs["slug"])

    @property
    def list_url(self):
        return reverse("archives:list")

    @property
    def form_url(self):
        return reverse(
            "archives:item-create", kwargs={"slug": self.base_object.slug}
        )

    @property
    def return_url(self):
        return reverse(
            "archives:items-list", kwargs={"slug": self.base_object.slug}
        )

    @property
    def new_interface_url(self):
        return reverse(
            "archives:item-new-interface-create",
            kwargs={"slug": self.base_object.slug},
        )

    def process_data_for_object(self, data):
        """Creates an archive item"""
        instance = ArchiveItem.objects.create(archive=self.base_object)
        for slug in data:
            instance.create_civ(
                ci_slug=slug, new_value=data[slug], user=self.request.user
            )
        return instance

    def get_success_url(self):
        return self.return_url


class ArchiveItemInterfaceCreate(InterfacesCreateBaseView):
    def get_required_permissions(self, request):
        if self.object:
            return [
                f"{Archive._meta.app_label}.change_{ArchiveItem._meta.model_name}"
            ]
        else:
            return [
                f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
            ]

    @property
    def object(self):
        if self.kwargs.get("pk"):
            return ArchiveItem.objects.get(pk=self.kwargs["pk"])
        else:
            return None

    @property
    def base_object(self):
        return Archive.objects.get(slug=self.kwargs["slug"])

    def get_htmx_url(self):
        if self.kwargs.get("pk") is not None:
            return reverse_lazy(
                "archives:item-interface-create",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "slug": self.base_object.slug,
                },
            )
        else:
            return reverse_lazy(
                "archives:item-new-interface-create",
                kwargs={"slug": self.base_object.slug},
            )
