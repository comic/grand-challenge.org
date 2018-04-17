# -*- coding: utf-8 -*-
from django.views.generic import CreateView, UpdateView

from grandchallenge.cases.forms import CaseForm
from grandchallenge.cases.models import Case


class CaseCreate(CreateView):
    model = Case
    form_class = CaseForm

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)



class CaseUpdate(UpdateView):
    model = Case
