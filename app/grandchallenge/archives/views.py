from django.views.generic import DetailView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.archives.models import Archive


class ArchiveList(PermissionListMixin, ListView):
    model = Archive
    permission_required = (
        f"{Archive._meta.app_label}.view_{Archive._meta.model_name}"
    )
    ordering = "-created"
    template_name = "base_card_list.html"


class ArchiveDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Archive
    permission_required = (
        f"{Archive._meta.app_label}.view_{Archive._meta.model_name}"
    )
    raise_exception = True
