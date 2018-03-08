from django.views.generic import ListView

from comicmodels.models import ComicSite
from comicsite.permissions.mixins import UserIsChallengeAdminMixin


class AdminsList(UserIsChallengeAdminMixin, ListView):
    template_name = 'admins/admins_list.html'

    def get_queryset(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_admins().select_related('user_profile')
