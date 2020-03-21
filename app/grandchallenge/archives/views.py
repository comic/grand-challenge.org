from dal import autocomplete
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
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

from grandchallenge.archives.forms import ArchiveForm, EditorsForm, UsersForm
from grandchallenge.archives.models import Archive
from grandchallenge.core.forms import UserFormKwargsMixin


class ArchiveList(PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
    ordering = "-created"


class ArchiveCreate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = UsersForm()
        form.fields["action"].initial = UsersForm.REMOVE
        context.update({"form": form})

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


class ArchiveUsersUpdate(ArchiveGroupUpdateMixin):
    form_class = UsersForm
    success_message = "Users successfully updated"
