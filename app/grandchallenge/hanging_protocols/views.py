from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import ContextMixin
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.hanging_protocols.forms import HangingProtocolForm
from grandchallenge.hanging_protocols.models import HangingProtocol
from grandchallenge.subdomains.utils import reverse


class HangingProtocolSvgIconContextDataMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data.update(
            {
                "svg_width_px": settings.HANGING_PROTOCOL_SVG_WIDTH,
                "svg_height_px": settings.HANGING_PROTOCOL_SVG_HEIGHT,
                "svg_stroke_width": settings.HANGING_PROTOCOL_SVG_WIDTH * 0.05,
            }
        )
        return data


class HangingProtocolList(
    HangingProtocolSvgIconContextDataMixin, LoginRequiredMixin, ListView
):
    model = HangingProtocol
    paginate_by = 50


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


class HangingProtocolDetail(
    HangingProtocolSvgIconContextDataMixin, LoginRequiredMixin, DetailView
):
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
