from django.views.generic import ListView

from grandchallenge.reader_studies.models import ReaderStudy


class ReaderStudyList(ListView):
    model = ReaderStudy
