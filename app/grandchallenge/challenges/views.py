from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import CreateView, ListView, UpdateView

from grandchallenge.challenges.forms import (
    ChallengeCreateForm,
    ChallengeUpdateForm,
    ExternalChallengeCreateForm,
    ExternalChallengeUpdateForm
)
from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.core.permissions.mixins import (
    UserIsChallengeAdminMixin, UserIsStaffMixin
)
from grandchallenge.core.urlresolvers import reverse


class ChallengeCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Challenge
    form_class = ChallengeCreateForm
    success_message = 'Challenge successfully created'

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class ChallengeList(ListView):
    model = Challenge

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(Q(hidden=False))


class UsersChallengeList(LoginRequiredMixin, ListView):
    model = Challenge
    template_name = "challenges/challenge_users_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(participants_group__in=self.request.user.groups.all()) |
                Q(admins_group__in=self.request.user.groups.all()) |
                Q(hidden=False)
            )
        return queryset


class ChallengeUpdate(
    UserIsChallengeAdminMixin, SuccessMessageMixin, UpdateView
):
    model = Challenge
    slug_field = 'short_name'
    slug_url_kwarg = 'challenge_short_name'
    form_class = ChallengeUpdateForm
    success_message = 'Challenge successfully updated'
    template_name_suffix = '_update'


class ExternalChallengeCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = ExternalChallenge
    form_class = ExternalChallengeCreateForm
    success_message = (
        "Your challenge has been successfully submitted. "
        "An admin will review your challenge before it is published."
    )

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("challenges:list")

class ExternalChallengeUpdate(
    UserIsStaffMixin, SuccessMessageMixin, UpdateView
):
    model = ExternalChallenge
    slug_field = "short_name"
    slug_url_kwarg = "short_name"
    form_class = ExternalChallengeUpdateForm
    template_name_suffix = "_update"
    success_message = "Challenge updated"

    def get_success_url(self):
        return reverse("challenges:list")
