from auth_mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import CreateView, ListView, UpdateView

from challenges.forms import ChallengeCreateForm, ChallengeUpdateForm
from challenges.models import Challenge
from core.permissions.mixins import UserIsChallengeAdminMixin


class ChallengeCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Challenge
    form_class = ChallengeCreateForm
    success_message = 'Challenge successfully created'

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(ChallengeCreate, self).form_valid(form)


class ChallengeList(LoginRequiredMixin, ListView):
    model = Challenge

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
