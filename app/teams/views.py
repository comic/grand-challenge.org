# Create your views here.
from django.views.generic import ListView, CreateView, UpdateView, DetailView

from comicmodels.models import ComicSite
from teams.models import Team


class TeamCreate(CreateView):
    model = Team
    fields = (
        'name',
        'website',
        'logo',
    )

    def form_valid(self, form):
        form.instance.challenge = ComicSite.objects.get(
            pk=self.request.project_pk)

        return super(TeamCreate, self).form_valid(form)


class TeamDetail(DetailView):
    model = Team


class TeamList(ListView):
    model = Team


class TeamUpdate(UpdateView):
    model = Team
    fields = (
        'name',
        'website',
        'logo',
    )
