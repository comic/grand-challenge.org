from grandchallenge.core.permissions.mixins import UserAuthAndTestMixin
from grandchallenge.teams.models import Team, TeamMember


class UserIsTeamOwnerOrChallengeAdminMixin(UserAuthAndTestMixin):
    def test_func(self):
        challenge = self.request.challenge
        team = Team.objects.get(pk=self.kwargs["pk"])
        return (self.request.user == team.owner) or challenge.is_admin(
            self.request.user
        )


class UserIsTeamMemberUserOrTeamOwnerOrChallengeAdminMixin(
    UserAuthAndTestMixin
):
    def test_func(self):
        challenge = self.request.challenge
        team_member = TeamMember.objects.get(pk=self.kwargs["pk"])
        return (
            (self.request.user == team_member.user)
            or (self.request.user == team_member.team.owner)
            or challenge.is_admin(self.request.user)
        )
