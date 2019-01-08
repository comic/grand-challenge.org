from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.shortcuts import get_current_site
from django.views.generic import ListView, FormView

from grandchallenge.admins.forms import AdminsForm
from grandchallenge.core.permissions.mixins import UserIsChallengeAdminMixin
from grandchallenge.subdomains.utils import reverse


class AdminsList(UserIsChallengeAdminMixin, ListView):
    template_name = "admins/templates/admins/admins_list.html"

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
        return challenge.get_admins().select_related("user_profile")


class AdminsUpdate(UserIsChallengeAdminMixin, SuccessMessageMixin, FormView):
    form_class = AdminsForm
    template_name = "admins/templates/admins/admins_form.html"
    success_message = "Admins successfully updated"

    def get_success_url(self):
        return reverse(
            "admins:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )

    def form_valid(self, form):
        challenge = self.request.challenge
        form.add_or_remove_user(
            challenge=challenge, site=get_current_site(self.request)
        )
        return super().form_valid(form)
