from django.views.generic import ListView, CreateView, DetailView, UpdateView
from guardian.mixins import PermissionListMixin, LoginRequiredMixin
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
)
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.reader_studies.forms import (
    ReaderStudyCreateForm,
    ReaderStudyUpdateForm,
    QuestionCreateForm,
)
from grandchallenge.reader_studies.models import ReaderStudy, Question, Answer
from grandchallenge.reader_studies.serializers import (
    ReaderStudySerializer,
    AnswerSerializer,
    QuestionSerializer,
)


class ReaderStudyList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{ReaderStudy._meta.model_name}"
    )


class ReaderStudyCreate(UserIsStaffMixin, CreateView):
    model = ReaderStudy
    form_class = ReaderStudyCreateForm

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.editors_group.user_set.add(self.request.user)
        return response


class ReaderStudyDetail(UserIsStaffMixin, DetailView):
    model = ReaderStudy


class ReaderStudyUpdate(UserIsStaffMixin, UpdateView):
    model = ReaderStudy
    form_class = ReaderStudyUpdateForm


class AddObjectToReaderStudyMixin:
    """
    Mixin that adds an object that has a foreign key to a reader study and a
    creator. The url to this view must include a slug that points to the slug
    of the reader study.
    """

    @property
    def reader_study(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.reader_study})
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.reader_study = self.reader_study
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.reader_study.get_absolute_url()


class AddImagesToReaderStudy(
    AddObjectToReaderStudyMixin, UserIsStaffMixin, CreateView
):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "reader_studies/readerstudy_add_images.html"


class AddQuestionToReaderStudy(
    AddObjectToReaderStudyMixin, UserIsStaffMixin, CreateView
):
    model = Question
    form_class = QuestionCreateForm
    template_name = "reader_studies/readerstudy_add_question.html"


class ReaderStudyViewSet(ReadOnlyModelViewSet):
    serializer_class = ReaderStudySerializer
    queryset = ReaderStudy.objects.all().prefetch_related(
        "images", "questions"
    )


class QuestionViewSet(ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all().select_related("reader_study")


class AnswerViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = AnswerSerializer
    queryset = (
        Answer.objects.all()
        .select_related("creator")
        .prefetch_related("images")
    )

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
