from auth_mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import CreateView, ListView

from challenges.forms import ChallengeForm
from comicmodels.models import ComicSite


class ChallengeCreate(LoginRequiredMixin, CreateView):
    model = ComicSite
    form_class = ChallengeForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(ChallengeCreate, self).form_valid(form)


class ChallengeList(LoginRequiredMixin, ListView):
    model = ComicSite

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(participants_group=self.request.user.groups.all()) |
                Q(admins_group=self.request.user.groups.all())
            )

        return queryset
