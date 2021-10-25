from celery import chain, chord, group
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.db.transaction import on_commit
from django.forms.utils import ErrorList
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.algorithms.tasks import (
    add_images_to_component_interface_value,
)
from grandchallenge.archives.filters import ArchiveFilter
from grandchallenge.archives.forms import (
    AddCasesForm,
    ArchiveCasesToReaderStudyForm,
    ArchiveForm,
    ArchiveItemForm,
    ArchivePermissionRequestUpdateForm,
    UploadersForm,
    UsersForm,
)
from grandchallenge.archives.models import (
    Archive,
    ArchiveItem,
    ArchivePermissionRequest,
)
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.archives.tasks import (
    add_images_to_archive,
    update_archive_item_values,
)
from grandchallenge.cases.models import (
    Image,
    RawImageUploadSession,
)
from grandchallenge.cases.tasks import build_images
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


class ArchiveList(FilterMixin, PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
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
                    random_encode("mailto:support@grand-challenge.org"),
                ),
            }
        )

        return context


class ArchiveCreate(
    PermissionRequiredMixin, UserFormKwargsMixin, CreateView,
):
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
            archive=context["object"], status=ArchivePermissionRequest.PENDING,
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


class ArchiveUploadersUpdate(ArchiveGroupUpdateMixin):
    form_class = UploadersForm
    success_message = "Uploaders successfully updated"


class ArchiveUsersUpdate(ArchiveGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"


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
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permission_request = ArchivePermissionRequest.objects.filter(
            archive=self.archive, user=self.request.user
        ).first()
        context.update(
            {
                "permission_request": permission_request,
                "archive": self.archive,
            }
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
                )
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
        f"{Archive._meta.app_label}.upload_{Archive._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.archive

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    @cached_property
    def archive_item(self):
        return get_object_or_404(ArchiveItem, pk=self.kwargs["id"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"archive": self.archive, "archive_item": self.archive_item}
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"archive": self.archive})
        return context

    def form_valid(self, form):  # noqa: C901
        def create_upload(image_files):
            upload_session = RawImageUploadSession.objects.create(
                creator=self.request.user
            )
            upload_session.user_uploads.set(image_files)
            return upload_session.pk

        upload_pks = {}
        civ_pks_to_remove = set()
        civ_pks_to_add = set()

        for slug, value in form.cleaned_data.items():
            if value is None:
                continue

            ci = ComponentInterface.objects.get(slug=slug)
            civ = self.archive_item.values.filter(interface=ci).first()

            if civ:
                if civ.value == value:
                    continue
                civ_pks_to_remove.add(civ.pk)

            if ci.kind in InterfaceKind.interface_type_image():
                if value:
                    civ = ComponentInterfaceValue.objects.create(interface=ci)
                    civ_pks_to_add.add(civ.pk)
                    upload_pks[civ.pk] = create_upload(value)
            elif ci.kind in InterfaceKind.interface_type_file():
                civ = ComponentInterfaceValue.objects.create(interface=ci)
                value.copy_object(to_field=civ.file)
                civ.full_clean()
                civ.save()
                value.delete()
                civ_pks_to_add.add(civ.pk)
            else:
                civ = ci.create_instance(value=value)
                civ_pks_to_add.add(civ.pk)

        tasks = update_archive_item_values.signature(
            kwargs={
                "archive_item_pk": self.archive_item.pk,
                "civ_pks_to_add": list(civ_pks_to_add),
                "civ_pks_to_remove": list(civ_pks_to_remove),
            },
            immutable=True,
        )

        if len(upload_pks) > 0:
            image_tasks = group(
                chain(
                    build_images.signature(
                        kwargs={"upload_session_pk": upload_pk}
                    ),
                    add_images_to_component_interface_value.signature(
                        kwargs={
                            "component_interface_value_pk": civ_pk,
                            "upload_session_pk": upload_pk,
                        },
                        immutable=True,
                    ),
                )
                for civ_pk, upload_pk in upload_pks.items()
            )
            tasks = chord(image_tasks, tasks)

        on_commit(tasks.apply_async)

        return HttpResponseRedirect(
            reverse(
                "archives:items-list", kwargs={"slug": self.kwargs["slug"]},
            )
        )


class ArchiveItemsList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView,
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
        Column(title="Edit", sort_field="pk"),
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
        return qs.filter(archive=self.archive).prefetch_related("values")


class ArchiveCasesList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView,
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
        Column(title="View", sort_field="pk"),
        Column(
            title="Algorithm Results",
            sort_field="pk",
            optional_condition=lambda o: any(
                civ.algorithms_jobs_as_input.exists()
                for civ in o.componentinterfacevalue_set.all()
            ),
        ),
        Column(title="Download", sort_field="pk"),
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


class ArchiveCasesToReaderStudyUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = ArchiveCasesToReaderStudyForm
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
        images = form.cleaned_data["images"]

        reader_study.images.add(*images)

        self.success_url = reader_study.get_absolute_url()
        self.success_message = f"Added {len(images)} cases to {reader_study}."

        return super().form_valid(form)


class ArchiveViewSet(ReadOnlyModelViewSet):
    serializer_class = ArchiveSerializer
    queryset = Archive.objects.all()
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = (
        DjangoFilterBackend,
        ObjectPermissionsFilter,
    )
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
