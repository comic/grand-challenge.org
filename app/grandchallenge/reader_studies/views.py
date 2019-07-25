from dal import autocomplete
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    FormView,
)
from guardian.mixins import (
    PermissionListMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
)
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet, GenericViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.reader_studies.forms import (
    ReaderStudyCreateForm,
    ReaderStudyUpdateForm,
    QuestionCreateForm,
    EditorsForm,
    ReadersForm,
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

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "user_can_add_reader_study": self.request.user.has_perm(
                    f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}"
                )
            }
        )
        return context


class ReaderStudyCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = ReaderStudy
    form_class = ReaderStudyCreateForm
    permission_required = (
        f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}"
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.add_editor(self.request.user)
        return response


class ReaderStudyDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{ReaderStudy._meta.model_name}"
    )


class ReaderStudyUpdate(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, UpdateView
):
    model = ReaderStudy
    form_class = ReaderStudyUpdateForm
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )


class AddObjectToReaderStudyMixin(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, CreateView
):
    """
    Mixin that adds an object that has a foreign key to a reader study and a
    creator. The url to this view must include a slug that points to the slug
    of the reader study.

    Must be placed to the left of ObjectPermissionRequiredMixin.
    """

    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )

    def get_permission_object(self):
        return self.reader_study

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


class AddImagesToReaderStudy(AddObjectToReaderStudyMixin):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "reader_studies/readerstudy_add_images.html"


class AddQuestionToReaderStudy(AddObjectToReaderStudyMixin):
    model = Question
    form_class = QuestionCreateForm
    template_name = "reader_studies/readerstudy_add_question.html"


class ReaderStudyUserAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        group_pks = (
            ReaderStudy.objects.all()
            .select_related("editors_group")
            .values_list("editors_group__pk", flat=True)
        )
        return self.request.user.groups.filter(pk__in=group_pks).exists()

    def get_queryset(self):
        qs = get_user_model().objects.all().order_by("username")

        if self.q:
            qs = qs.filter(username__istartswith=self.q)

        return qs


class ReaderStudyUserGroupUpdateMixin(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    template_name = "reader_studies/readerstudy_user_groups_form.html"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"object": self.reader_study, "role": self.get_form().role}
        )
        return context

    def get_success_url(self):
        return self.reader_study.get_absolute_url()

    def form_valid(self, form):
        form.add_or_remove_user(reader_study=self.reader_study)
        return super().form_valid(form)


class EditorsUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class ReadersUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = ReadersForm
    success_message = "Readers successfully updated"


class ReaderStudyViewSet(ReadOnlyModelViewSet):
    serializer_class = ReaderStudySerializer
    queryset = ReaderStudy.objects.all().prefetch_related(
        "images", "questions"
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoObjectPermissionsFilter]


class QuestionViewSet(ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all().select_related("reader_study")
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoObjectPermissionsFilter]


class AnswerViewSet(
    CreateModelMixin, RetrieveModelMixin, ListModelMixin, GenericViewSet
):
    serializer_class = AnswerSerializer
    queryset = (
        Answer.objects.all()
        .select_related("creator")
        .prefetch_related("images")
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoObjectPermissionsFilter]

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)
