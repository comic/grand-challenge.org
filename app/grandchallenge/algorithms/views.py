# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView

from grandchallenge.algorithms.models import Algorithm


class AlgorithmList(ListView):
    model = Algorithm

class AlgorithmCreate(LoginRequiredMixin, CreateView):
    # TODO: Permissions
    # TODO: Chunked uploads
    model = Algorithm
    fields = '__all__'
