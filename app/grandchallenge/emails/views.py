from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.emails.forms import EmailForm
from grandchallenge.emails.models import Email


class EmailCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Email
    form_class = EmailForm
    permission_required = "emails.add_email"
    raise_exception = True


class EmailUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Email
    form_class = EmailForm
    permission_required = "emails.change_email"
    raise_exception = True

    def has_permission(self):
        if self.get_object().sent:
            raise PermissionDenied
        else:
            return super().has_permission()


class EmailDetail(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Email
    permission_required = "emails.view_email"
    raise_exception = True


class EmailList(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Email
    permission_required = "emails.view_email"
    raise_exception = True
    paginate_by = 50
