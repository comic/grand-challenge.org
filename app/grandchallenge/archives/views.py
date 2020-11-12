from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.db.models import Count
from django.forms.utils import ErrorList
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
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
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.archives.forms import (
    ArchiveCasesToReaderStudyForm,
    ArchiveForm,
    ArchivePermissionRequestUpdateForm,
    EditorsForm,
    UploadersForm,
    UsersForm,
)
from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.archives.serializers import ArchiveSerializer
from grandchallenge.archives.tasks import add_images_to_archive
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.views import RawImageUploadSessionDetail
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyPermissions,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


class ArchiveList(PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
    ordering = "-created"

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset()
        queryset = (queryset | Archive.objects.filter(public=True)).distinct()
        return queryset

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
        f"{model._meta.app_label}.view_{model._meta.model_name}"
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
                "offsets": range(0, context["object"].images.count(), limit),
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
    UserFormKwargsMixin,
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Archive
    form_class = ArchiveForm
    permission_required = (
        f"{model._meta.app_label}.change_{model._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ArchiveUsersAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        group_pks = (
            Archive.objects.all()
            .select_related("editors_group")
            .values_list("editors_group__pk", flat=True)
        )
        return (
            self.request.user.is_superuser
            or self.request.user.groups.filter(pk__in=group_pks).exists()
        )

    def get_queryset(self):
        qs = (
            get_user_model()
            .objects.all()
            .order_by("username")
            .exclude(username=settings.ANONYMOUS_USER_NAME)
        )

        if self.q:
            qs = qs.filter(username__istartswith=self.q)

        return qs


class ArchiveGroupUpdateMixin(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    template_name = "archives/archive_user_groups_form.html"
    permission_required = (
        f"{Archive._meta.app_label}.change_{Archive._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.archive

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.archive, "role": self.get_form().role})
        return context

    def get_success_url(self):
        return self.archive.get_absolute_url()

    def form_valid(self, form):
        form.add_or_remove_user(archive=self.archive)
        return super().form_valid(form)


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
    UserIsNotAnonMixin, SuccessMessageMixin, CreateView
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
    UserFormKwargsMixin,
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    CreateView,
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "archives/archive_upload_session_create.html"
    permission_required = (
        f"{Archive._meta.app_label}.upload_{Archive._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"linked_task": add_images_to_archive})
        return kwargs

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.archive = self.archive
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context

    def get_success_url(self):
        return reverse(
            "archives:uploads-detail",
            kwargs={"slug": self.archive.slug, "pk": self.object.pk},
        )


class ArchiveUploadSessionDetail(RawImageUploadSessionDetail):
    template_name = "archives/archive_upload_session_detail.html"

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context


class ArchiveUploadSessionList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, ListView
):
    model = RawImageUploadSession
    permission_required = (
        f"{Archive._meta.app_label}.upload_{Archive._meta.model_name}"
    )
    raise_exception = True
    template_name = "archives/archive_upload_session_list.html"

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return (
            qs.filter(archive=self.archive)
            .select_related("creator__user_profile", "creator__verification")
            .annotate(Count("image", distinct=True),)
        )


class ArchiveCasesList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, ListView
):
    model = Image
    permission_required = (
        f"{Archive._meta.app_label}.view_{Archive._meta.model_name}"
    )
    raise_exception = True
    template_name = "archives/archive_cases_list.html"

    @cached_property
    def archive(self):
        return get_object_or_404(Archive, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.archive

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"archive": self.archive})
        return context

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        return (
            qs.filter(archive=self.archive)
            .prefetch_related(
                "files",
                "componentinterfacevalue_set__algorithms_jobs_as_input__outputs__image__files",
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
        f"{Archive._meta.app_label}.view_{Archive._meta.model_name}"
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
    permission_classes = (DjangoObjectOnlyPermissions,)
    filter_backends = (ObjectPermissionsFilter,)
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )
