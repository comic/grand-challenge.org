from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import CreateView, DetailView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.archives.forms import ArchiveForm
from grandchallenge.archives.models import Archive


class ArchiveList(PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
    ordering = "-created"


class ArchiveCreate(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Archive
    form_class = ArchiveForm
    permission_required = (
        f"{model._meta.app_label}.add_{model._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form=form)
        self.object.add_editor(self.request.user)
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class ArchiveDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Archive
    permission_required = (
        f"{model._meta.app_label}.view_{model._meta.model_name}"
    )
    raise_exception = True
