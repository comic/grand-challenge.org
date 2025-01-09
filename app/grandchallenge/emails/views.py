from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.emails.forms import EmailBodyForm, EmailMetadataForm
from grandchallenge.emails.models import Email
from grandchallenge.subdomains.utils import reverse


class EmailCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Email
    form_class = EmailMetadataForm
    permission_required = "emails.add_email"
    raise_exception = True

    def get_success_url(self):
        """On successful creation, go to content update."""
        return reverse(
            "emails:body-update",
            kwargs={
                "pk": self.object.pk,
            },
        )


class UnsentEmailRequiredMixin:
    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)

        if obj.sent:
            raise PermissionDenied
        else:
            return obj


class EmailMetadataUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UnsentEmailRequiredMixin,
    UpdateView,
):
    model = Email
    form_class = EmailMetadataForm
    permission_required = "emails.change_email"
    raise_exception = True


class EmailBodyUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UnsentEmailRequiredMixin,
    UpdateView,
):
    model = Email
    form_class = EmailBodyForm
    template_name_suffix = "_body_update"
    permission_required = "emails.change_email"
    raise_exception = True


class EmailDetail(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Email
    permission_required = "emails.view_email"
    raise_exception = True


@method_decorator(xframe_options_sameorigin, name="dispatch")
class RenderedEmailDetail(
    LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    model = Email
    template_name_suffix = "_rendered_detail"
    permission_required = "emails.view_email"
    raise_exception = True

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        self.object.body = request.POST["content"]

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class EmailList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Email
    permission_required = "emails.view_email"
    raise_exception = True
    paginate_by = 50
