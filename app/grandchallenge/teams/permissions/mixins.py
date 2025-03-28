from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import get_object_or_404

from grandchallenge.teams.models import Team, TeamMember


class UserIsTeamOwnerOrChallengeAdminMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        challenge = request.challenge
        team = get_object_or_404(Team, pk=kwargs["pk"])
        if (request.user == team.owner) or challenge.is_admin(request.user):
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()


class UserIsTeamMemberUserOrTeamOwnerOrChallengeAdminMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        challenge = request.challenge
        team_member = get_object_or_404(TeamMember, pk=kwargs["pk"])
        if (
            (request.user == team_member.user)
            or (request.user == team_member.team.owner)
            or challenge.is_admin(request.user)
        ):
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()


class UserIsChallengeParticipantOrAdminMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        challenge = request.challenge
        if challenge.is_admin(user) or challenge.is_participant(user):
            return super().dispatch(request, *args, **kwargs)
        else:
            return self.handle_no_permission()
