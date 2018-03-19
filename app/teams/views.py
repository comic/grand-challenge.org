from django.contrib import messages
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.models import Q
from django.forms.utils import ErrorList
from django.views.generic import (
    ListView, CreateView, UpdateView, DetailView, DeleteView
)

from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeParticipantOrAdminMixin
from teams.models import Team, TeamMember
from teams.permissions.mixins import (
    UserIsTeamOwnerOrChallengeAdminMixin,
    UserIsTeamMemberUserOrTeamOwnerOrChallengeAdminMixin,
)


class TeamCreate(UserIsChallengeParticipantOrAdminMixin, CreateView):
    model = Team
    fields = ('name', 'department', 'institution', 'website')

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        form.instance.owner = self.request.user
        try:
            return super(TeamCreate, self).form_valid(form)

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super(TeamCreate, self).form_invalid(form)


class TeamDetail(DetailView):
    model = Team

    def get_context_data(self, **kwargs):
        context = super(TeamDetail, self).get_context_data(**kwargs)
        try:
            team = TeamMember.objects.get(
                team__challenge=self.request.challenge,
                user__pk=self.request.user.pk,
            )
        except TeamMember.DoesNotExist:
            team = None
        context.update({'user_team': team})
        return context


class TeamList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Team

    def get_context_data(self, **kwargs):
        context = super(TeamList, self).get_context_data(**kwargs)
        users_teams = TeamMember.objects.filter(
            team__challenge=self.request.challenge, user=self.request.user
        )
        context.update({'users_teams': users_teams})
        return context

    def get_queryset(self):
        queryset = super(TeamList, self).get_queryset()
        return queryset.filter(Q(challenge=self.request.challenge))


class TeamUpdate(UserIsTeamOwnerOrChallengeAdminMixin, UpdateView):
    model = Team
    fields = ('name', 'website', 'department', 'institution')


class TeamDelete(UserIsTeamOwnerOrChallengeAdminMixin, DeleteView):
    model = Team
    success_message = 'Team successfully deleted'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(TeamDelete, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'teams:list',
            kwargs={'challenge_short_name': self.object.challenge.short_name},
        )


class TeamMemberCreate(UserIsChallengeParticipantOrAdminMixin, CreateView):
    model = TeamMember
    fields = ()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.team = Team.objects.get(pk=self.kwargs['pk'])
        try:
            return super(TeamMemberCreate, self).form_valid(form)

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super(TeamMemberCreate, self).form_invalid(form)

    def get_success_url(self):
        return self.object.team.get_absolute_url()


class TeamMemberDelete(
    UserIsTeamMemberUserOrTeamOwnerOrChallengeAdminMixin, DeleteView
):
    model = TeamMember
    success_message = 'User successfully removed from team'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(TeamMemberDelete, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'teams:list',
            kwargs={
                'challenge_short_name': self.object.team.challenge.short_name
            },
        )
