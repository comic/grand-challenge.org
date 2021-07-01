from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import FormView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.admins.forms import AdminsForm
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class AdminsList(LoginRequiredMixin, ObjectPermissionRequiredMixin, ListView):
    template_name = "admins/admins_list.html"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "this_admin_pk": self.request.user.pk,
                "admin_remove_action": AdminsForm.REMOVE,
            }
        )
        return context

    def get_queryset(self):
        challenge = self.request.challenge
        return challenge.get_admins().select_related(
            "user_profile", "verification"
        )


class AdminsUpdateAutocomplete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    autocomplete.Select2QuerySetView,
):
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_queryset(self):
        qs = get_user_model().objects.all().order_by("username")

        if self.q:
            qs = qs.filter(username__istartswith=self.q)

        return qs


class AdminsUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = AdminsForm
    template_name = "admins/admins_form.html"
    success_message = "Admins successfully updated"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_success_url(self):
        return reverse(
            "admins:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )

    def form_valid(self, form):
        challenge = self.request.challenge
        form.add_or_remove_user(challenge=challenge, site=self.request.site)
        return super().form_valid(form)
