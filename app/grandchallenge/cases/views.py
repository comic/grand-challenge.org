# -*- coding: utf-8 -*-
from django.views.generic import CreateView, UpdateView, DetailView

from grandchallenge.cases.forms import CaseForm
from grandchallenge.cases.models import Case
from grandchallenge.core.urlresolvers import reverse


class CaseCreate(CreateView):
    # TODO: challenge admin only

    model = Case
    form_class = CaseForm

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'cases:update',
            kwargs={
                'challenge_short_name': self.object.challenge,
                'pk': self.object.pk,
            }
        )

class CaseDetail(DetailView):
    model = Case


class CaseUpdate(UpdateView):
    model = Case
    form_class = CaseForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(

        )

        return context
