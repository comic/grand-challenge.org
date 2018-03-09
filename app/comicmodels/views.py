from auth_mixins import LoginRequiredMixin
from django.views.generic import CreateView

from comicmodels.forms import ChallengeForm
from comicmodels.models import ComicSite


class ChallengeCreate(LoginRequiredMixin, CreateView):
    model = ComicSite
    form_class = ChallengeForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(ChallengeCreate, self).form_valid(form)
