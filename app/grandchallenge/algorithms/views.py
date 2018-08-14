# -*- coding: utf-8 -*-
import logging

from django.core.files import File
from django.views.generic import ListView, CreateView, DetailView
from nbconvert import HTMLExporter

from grandchallenge.algorithms.forms import AlgorithmForm, JobForm
from grandchallenge.algorithms.models import Algorithm, Job, Result
from tests.core_tests.test_permissions import StaffOnlyView

logger = logging.getLogger(__name__)


class AlgorithmList(StaffOnlyView, ListView):
    model = Algorithm


def ipynb_to_html(*, notebook: File):
    # Run nbconvert on the description and get the html on each save
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'full'

    with notebook.open() as d:
        (body, _) = html_exporter.from_file(d)

    return body


class AlgorithmCreate(StaffOnlyView, CreateView):
    model = Algorithm
    form_class = AlgorithmForm

    def form_valid(self, form):
        try:
            form.instance.description_html = ipynb_to_html(
                notebook=form.cleaned_data["ipython_notebook"]
            )
        except AttributeError:
            logger.warning("Could not convert notebook to html.")

        form.instance.creator = self.request.user
        uploaded_file = form.cleaned_data['chunked_upload'][0]
        with uploaded_file.open() as f:
            form.instance.image.save(uploaded_file.name, File(f))

        return super().form_valid(form)


class AlgorithmDetail(StaffOnlyView, DetailView):
    model = Algorithm


class JobList(StaffOnlyView, ListView):
    model = Job


class JobCreate(StaffOnlyView, CreateView):
    model = Job
    form_class = JobForm


class JobDetail(StaffOnlyView, DetailView):
    model = Job


class ResultList(StaffOnlyView, ListView):
    model = Result


class ResultDetail(StaffOnlyView, DetailView):
    model = Result
