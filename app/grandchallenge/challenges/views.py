from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import (
    CreateView,
    ListView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from grandchallenge.challenges.forms import (
    ChallengeCreateForm,
    ChallengeUpdateForm,
    ExternalChallengeUpdateForm,
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


class ChallengeList(TemplateView):
    template_name = "challenges/challenge_list.html"

    @staticmethod
    def create_objects_by_year(queryset, existing=None):
        if existing is None:
            existing = defaultdict(list)

        for q in queryset:
            existing[q.year].append(q)

        return existing

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()

        challenges_by_year = self.create_objects_by_year(
            Challenge.objects
                .filter(hidden=False)
                .order_by("-created_at")
        )
        challenges_by_year = self.create_objects_by_year(
            ExternalChallenge.objects
                .filter(hidden=False)
                .order_by("-created_at"),
            challenges_by_year
        )

        context.update({"challenges_by_year": dict(challenges_by_year)})

        return context


class UsersChallengeList(LoginRequiredMixin, ListView):
    model = Challenge
    template_name = "challenges/challenge_users_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(participants_group__in=self.request.user.groups.all()) |
                Q(admins_group__in=self.request.user.groups.all())
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
    UserIsStaffMixin, SuccessMessageMixin, CreateView
):
    model = ExternalChallenge
    form_class = ExternalChallengeUpdateForm
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


class ExternalChallengeList(UserIsStaffMixin, ListView):
    model = ExternalChallenge


class ExternalChallengeDelete(UserIsStaffMixin, DeleteView):
    model = ExternalChallenge
    slug_field = "short_name"
    slug_url_kwarg = "short_name"
    success_message = "External challenge was successfully deleted"

    def get_success_url(self):
        return reverse("challenges:external-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
