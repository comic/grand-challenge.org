from django.views.generic import ListView, CreateView, UpdateView, DetailView, \
    DeleteView

from comicmodels.models import ComicSite
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeParticipantOrAdminMixin
from teams.models import Team, TeamMember
from teams.permissions.mixins import UserIsTeamAdminMixin


class TeamCreate(UserIsChallengeParticipantOrAdminMixin, CreateView):
    model = Team
    fields = (
        'name',
        'website',
        'logo',
    )

    def form_valid(self, form):
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)
        form.instance.creator = self.request.user

        return super(TeamCreate, self).form_valid(form)


class TeamDetail(UserIsChallengeParticipantOrAdminMixin, DetailView):
    model = Team


class TeamList(UserIsChallengeParticipantOrAdminMixin, ListView):
    model = Team

    def get_context_data(self, **kwargs):
        context = super(TeamList, self).get_context_data()

        member_of = TeamMember.objects.filter(
            team__challenge=self.request.project_pk,
            user=self.request.user,
        )

        context.update({'member_of': member_of})

        return context


class TeamUpdate(UserIsTeamAdminMixin, UpdateView):
    model = Team
    fields = (
        'name',
        'website',
        'logo',
    )


class TeamMemberCreate(UserIsChallengeParticipantOrAdminMixin, CreateView):
    model = TeamMember
    fields = ()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.team = Team.objects.get(pk=self.kwargs['pk'])

        return super(TeamMemberCreate, self).form_valid(form)

    def get_success_url(self):
        return self.object.team.get_absolute_url()


class TeamMemberDelete(DeleteView):
    model = TeamMember

    def get_success_url(self):
        return reverse(
            'teams:list',
            kwargs={
                'challenge_short_name': self.object.team.challenge.short_name
            }
        )
