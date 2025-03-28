from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.hanging_protocols.forms import HangingProtocolForm
from grandchallenge.hanging_protocols.models import HangingProtocol
from grandchallenge.subdomains.utils import reverse


class HangingProtocolList(LoginRequiredMixin, ListView):
    model = HangingProtocol
    paginate_by = 48


class HangingProtocolCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = HangingProtocol
    form_class = HangingProtocolForm
    permission_required = f"{HangingProtocol._meta.app_label}.add_{HangingProtocol._meta.model_name}"
    success_message = "Hanging protocol successfully added"

    def get_success_url(self):
        return reverse("hanging-protocols:list")

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class HangingProtocolDetail(LoginRequiredMixin, DetailView):
    model = HangingProtocol


class HangingProtocolUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = HangingProtocol
    form_class = HangingProtocolForm
    permission_required = "change_hangingprotocol"
    raise_exception = True
    success_message = "Hanging protocol successfully updated"

    def get_success_url(self):
        return reverse("hanging-protocols:list")
