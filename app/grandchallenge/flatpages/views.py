from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.flatpages.models import FlatPage
from django.views.generic import CreateView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.flatpages.forms import FlatPageForm, FlatPageUpdateForm
from grandchallenge.subdomains.utils import reverse_lazy


class FlatPageUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = FlatPage
    form_class = FlatPageUpdateForm
    permission_required = "flatpages.change_flatpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class FlatPageCreate(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = FlatPage
    form_class = FlatPageForm
    permission_required = "flatpages.add_flatpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")
