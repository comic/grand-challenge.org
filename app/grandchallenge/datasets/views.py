from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.datasets.forms import (
    AnnotationSetForm,
    AnnotationSetUpdateForm,
    AnnotationSetUpdateLabelsForm,
    ImageSetUpdateForm,
)
from grandchallenge.datasets.models import AnnotationSet, ImageSet
from grandchallenge.datasets.utils import process_csv_file
from grandchallenge.pages.views import ChallengeFilteredQuerysetMixin
from grandchallenge.subdomains.utils import reverse


class ImageSetList(UserIsStaffMixin, ChallengeFilteredQuerysetMixin, ListView):
    model = ImageSet


class AddImagesToImageSet(UserIsStaffMixin, CreateView):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "datasets/imageset_add_images.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        imageset = ImageSet.objects.get(pk=self.kwargs["pk"])
        context.update({"phase_display": imageset.get_phase_display()})
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.imageset = ImageSet.objects.get(pk=self.kwargs["pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.imageset.get_absolute_url()


class ImageSetUpdate(UserIsStaffMixin, UpdateView):
    model = ImageSet
    form_class = ImageSetUpdateForm
    template_name_suffix = "_update"


class ImageSetDetail(UserIsStaffMixin, DetailView):
    model = ImageSet


class AnnotationSetList(UserIsStaffMixin, ListView):
    model = AnnotationSet

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(base__pk=self.kwargs["base_pk"])


class AnnotationSetCreate(UserIsStaffMixin, CreateView):
    model = AnnotationSet
    form_class = AnnotationSetForm

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.base = ImageSet.objects.get(pk=self.kwargs["base_pk"])
        return super().form_valid(form=form)

    def get_success_url(self):
        return reverse(
            "datasets:annotationset-add-images",
            kwargs={
                "challenge_short_name": self.object.base.challenge.short_name,
                "pk": self.object.pk,
            },
        )


class AnnotationSetUpdateContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        annotationset = AnnotationSet.objects.get(pk=self.kwargs["pk"])
        context.update(
            {
                "kind_display": annotationset.get_kind_display(),
                "phase_display": annotationset.base.get_phase_display(),
            }
        )
        return context


class AddImagesToAnnotationSet(
    UserIsStaffMixin, AnnotationSetUpdateContextMixin, CreateView
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "datasets/annotationset_add_images.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        annotationset = AnnotationSet.objects.get(pk=self.kwargs["pk"])
        context.update(
            {
                "kind_display": annotationset.get_kind_display(),
                "phase_display": annotationset.base.get_phase_display(),
            }
        )
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.annotationset = AnnotationSet.objects.get(
            pk=self.kwargs["pk"]
        )
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.annotationset.get_absolute_url()


class AnnotationSetUpdateLabels(
    UserIsStaffMixin, AnnotationSetUpdateContextMixin, UpdateView
):
    model = AnnotationSet
    form_class = AnnotationSetUpdateLabelsForm
    template_name_suffix = "_update_labels"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["chunked_upload"][0]

        with uploaded_file.open() as f:
            form.instance.labels = process_csv_file(f)

        return super().form_valid(form)


class AnnotationSetUpdate(UserIsStaffMixin, UpdateView):
    model = AnnotationSet
    form_class = AnnotationSetUpdateForm
    template_name_suffix = "_update"


class AnnotationSetDetail(UserIsStaffMixin, DetailView):
    model = AnnotationSet
