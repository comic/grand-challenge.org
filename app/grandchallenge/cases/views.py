# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files import File
from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.cases.forms import CaseForm
from grandchallenge.cases.models import Case


class CaseList(ListView):
    model = Case


class CaseCreate(LoginRequiredMixin, CreateView):
    model = Case
    form_class = CaseForm

    def form_valid(self, form):
        form.instance.creator = self.request.user

        uploaded_file = form.cleaned_data['chunked_upload'][0]
        with uploaded_file.open() as f:
            form.instance.file.save(uploaded_file.name, File(f))

        return super().form_valid(form)


class CaseDetail(DetailView):
    model = Case
