from django.views.generic import ListView, FormView

from admins.forms import AdminsForm
from comicmodels.models import ComicSite
from comicsite.core.urlresolvers import reverse
from comicsite.permissions.mixins import UserIsChallengeAdminMixin


class AdminsList(UserIsChallengeAdminMixin, ListView):
    template_name = 'admins/admins_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'this_admin_pk': self.request.user.pk,
            'admin_remove_action': AdminsForm.REMOVE,
        })
        return context

    def get_queryset(self):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        return challenge.get_admins().select_related('user_profile')


class AdminsUpdate(UserIsChallengeAdminMixin, FormView):
    form_class = AdminsForm
    template_name = 'admins/admins_form.html'

    def get_success_url(self):
        return reverse(
            'admins:list',
            kwargs={
                'challenge_short_name': self.request.projectname
            }
        )

    def form_valid(self, form):
        challenge = ComicSite.objects.get(pk=self.request.project_pk)
        form.add_or_remove_user(challenge)
        return super().form_valid(form)
