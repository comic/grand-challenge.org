from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.reader_studies.forms import ReaderStudyCreateForm
from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudyList(ListView):
    model = ReaderStudy


class ReaderStudyCreate(CreateView):
    model = ReaderStudy
    form_class = ReaderStudyCreateForm


class ReaderStudyDetail(DetailView):
    model = ReaderStudy
