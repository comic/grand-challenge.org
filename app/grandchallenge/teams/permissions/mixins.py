from django.shortcuts import get_object_or_404

from grandchallenge.core.models import UserPassesTestMixin
from grandchallenge.teams.models import Team, TeamMember


class UserIsTeamOwnerOrChallengeAdminMixin(UserPassesTestMixin):
    def test_func(self):
        challenge = self.request.challenge
        team = get_object_or_404(Team, pk=self.kwargs["pk"])
        if (self.request.user == team.owner) or challenge.is_admin(
            self.request.user
        ):
            return super().test_func()
        else:
            return False


class UserIsTeamMemberUserOrTeamOwnerOrChallengeAdminMixin(
    UserPassesTestMixin
):
    def test_func(self):
        challenge = self.request.challenge
        team_member = get_object_or_404(TeamMember, pk=self.kwargs["pk"])
        if (
            (self.request.user == team_member.user)
            or (self.request.user == team_member.team.owner)
            or challenge.is_admin(self.request.user)
        ):
            return super().test_func()
        else:
            return False


class UserIsChallengeParticipantOrAdminMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        challenge = self.request.challenge
        if challenge.is_admin(user) or challenge.is_participant(user):
            return super().test_func()
        else:
            return False
