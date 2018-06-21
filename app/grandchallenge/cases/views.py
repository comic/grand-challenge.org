# -*- coding: utf-8 -*-
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files import File
from django.views.generic import ListView, CreateView, DetailView

from grandchallenge.cases.forms import CaseForm, UploadRawImagesForm
from grandchallenge.cases.models import Case, CaseFile, RawImageFile, \
    RawImageUploadSession, UPLOAD_SESSION_STATE


class CaseList(ListView):
    model = Case


class CaseCreate(LoginRequiredMixin, CreateView):
    model = Case
    form_class = CaseForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        redirect = super().form_valid(form)

        for uploaded_file in form.cleaned_data['chunked_upload']:
            with uploaded_file.open() as f:
                case_file = CaseFile.objects.create(
                    case=self.object,
                )
                case_file.file.save(uploaded_file.name, File(f))

        return redirect


class CaseDetail(DetailView):
    model = Case


class UploadRawFiles(LoginRequiredMixin, CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        redirect = super().form_valid(form)

        return redirect


class ShowUploadSessionState(DetailView):
    model = RawImageUploadSession

    def get_context_data(self, **kwargs):
        result = super(ShowUploadSessionState, self).get_context_data(**kwargs)
        result["upload_session"] = result["object"]
        result["raw_files"] = \
            RawImageFile.objects.filter(upload_session=result["object"]).all()
        result["process_finished"] = result["object"].session_state == UPLOAD_SESSION_STATE.stopped
        return result
