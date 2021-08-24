import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.forms.utils import ErrorList
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from django_filters.rest_framework import DjangoFilterBackend
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from guardian.shortcuts import get_perms
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import (
    GenericViewSet,
    ReadOnlyModelViewSet,
)
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.filters import (
    AnswerFilter,
    ReaderStudyFilter,
)
from grandchallenge.reader_studies.forms import (
    AnswersRemoveForm,
    CategoricalOptionFormSet,
    GroundTruthForm,
    QuestionForm,
    ReaderStudyCopyForm,
    ReaderStudyCreateForm,
    ReaderStudyPermissionRequestUpdateForm,
    ReaderStudyUpdateForm,
    ReadersForm,
)
from grandchallenge.reader_studies.models import (
    Answer,
    CategoricalOption,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from grandchallenge.reader_studies.serializers import (
    AnswerSerializer,
    QuestionSerializer,
    ReaderStudySerializer,
)
from grandchallenge.reader_studies.tasks import add_images_to_reader_study
from grandchallenge.subdomains.utils import reverse


class ReaderStudyList(FilterMixin, PermissionListMixin, ListView):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{ReaderStudy._meta.model_name}"
    )
    ordering = "-created"
    filter_class = ReaderStudyFilter
    paginate_by = 40

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "jumbotron_title": "Reader Studies",
                "jumbotron_description": format_html(
                    (
                        "A reader study can be used to collect annotations or "
                        "score algorithm results for a set of medical images. "
                        "Please <a href='{}'>contact us</a> if you would like "
                        "to set up your own reader study."
                    ),
                    random_encode("mailto:support@grand-challenge.org"),
                ),
            }
        )

        return context


class ReaderStudyCreate(
    PermissionRequiredMixin, UserFormKwargsMixin, CreateView,
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


class ReaderStudyExampleGroundTruth(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    def get(self, request, *args, **kwargs):
        reader_study = self.get_object()
        response = HttpResponse(content_type="text/csv")
        response[
            "Content-Disposition"
        ] = f'attachment; filename="ground-truth-{reader_study.slug}"'
        writer = csv.DictWriter(
            response,
            fieldnames=reader_study.ground_truth_file_headers,
            escapechar="\\",
            quoting=csv.QUOTE_NONE,
            quotechar="`",
        )
        writer.writeheader()
        writer.writerows(reader_study.get_ground_truth_csv_dict())

        return response


class ReaderStudyDetail(ObjectPermissionRequiredMixin, DetailView):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    def on_permission_check_fail(self, request, response, obj=None):
        response = self.get(request)
        return response

    def check_permissions(self, request):
        try:
            return super().check_permissions(request)
        except PermissionDenied:
            return HttpResponseRedirect(
                reverse(
                    "reader-studies:permission-request-create",
                    kwargs={"slug": self.object.slug},
                )
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_perms = get_perms(self.request.user, self.object)

        if f"change_{ReaderStudy._meta.model_name}" in object_perms:
            reader_remove_form = ReadersForm()
            reader_remove_form.fields["action"].initial = ReadersForm.REMOVE

            editor_remove_form = EditorsForm()
            editor_remove_form.fields["action"].initial = EditorsForm.REMOVE

            pending_permission_requests = ReaderStudyPermissionRequest.objects.filter(
                reader_study=context["object"],
                status=ReaderStudyPermissionRequest.PENDING,
            ).count()

            readers = (
                self.object.readers_group.user_set.select_related(
                    "user_profile", "verification"
                )
                .order_by("username")
                .all()
            )

            context.update(self._reader_study_export_context)

            context.update(
                {
                    "readers": readers,
                    "num_readers": self.object.readers_group.user_set.count(),
                    "reader_remove_form": reader_remove_form,
                    "editor_remove_form": editor_remove_form,
                    "example_ground_truth": self.object.get_example_ground_truth_csv_text(
                        limit=2
                    ),
                    "pending_permission_requests": pending_permission_requests,
                }
            )

        if f"read_{ReaderStudy._meta.model_name}" in object_perms:
            user_progress = self.object.get_progress_for_user(
                self.request.user
            )
            context.update(
                {
                    "progress": user_progress,
                    "user_score": self.object.score_for_user(
                        self.request.user
                    ),
                    "answerable_questions": self.object.answerable_question_count
                    * len(self.object.hanging_list),
                }
            )

        return context

    @property
    def _reader_study_export_context(self):
        limit = 1000
        return {
            "limit": limit,
            "now": now().isoformat(),
            "answer_offsets": range(
                0,
                Answer.objects.filter(
                    question__reader_study=self.object
                ).count(),
                limit,
            ),
            "image_offsets": range(0, self.object.images.count(), limit),
        }


class ReaderStudyUpdate(
    LoginRequiredMixin,
    UserFormKwargsMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = ReaderStudy
    form_class = ReaderStudyUpdateForm
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    success_message = "Reader study successfully updated"


class ReaderStudyDelete(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    success_message = "Reader study was successfully deleted"

    def get_success_url(self):
        return reverse("reader-studies:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)


class ReaderStudyLeaderBoard(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    template_name = "reader_studies/readerstudy_leaderboard.html"


class ReaderStudyStatistics(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    template_name = "reader_studies/readerstudy_statistics.html"
    # TODO: this view also contains the ground truth answer values.
    # If the permission is changed to 'read', we need to filter these values out.


class ReaderStudyImagesList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView
):
    model = Image
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    template_name = "reader_studies/readerstudy_images_list.html"
    row_template = "reader_studies/readerstudy_images_row.html"
    search_fields = ["pk", "name"]
    columns = [
        Column(title="Name", sort_field="name"),
        Column(title="Created", sort_field="created"),
        Column(title="Creator", sort_field="origin__creator__username"),
        Column(title="View", sort_field="pk"),
        Column(title="Download", sort_field="pk"),
        Column(title="Remove from Study", sort_field="pk"),
    ]

    @cached_property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.reader_study

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"reader_study": self.reader_study})
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs.filter(readerstudies=self.reader_study)
            .prefetch_related("files",)
            .select_related(
                "origin__creator__user_profile",
                "origin__creator__verification",
            )
        )


class QuestionOptionMixin:
    def validate_options(self, form, _super):
        context = self.get_context_data()
        options = context["options"]
        if form.data["answer_type"] not in [
            Question.AnswerType.CHOICE,
            Question.AnswerType.MULTIPLE_CHOICE,
            Question.AnswerType.MULTIPLE_CHOICE_DROPDOWN,
        ]:
            if getattr(self, "object", None):
                self.object.options.all().delete()
            return _super.form_valid(form)
        data = options.cleaned_data
        if len(list(filter(lambda x: x.get("default"), data))) > 1:
            error = ["Only one option can be the default option"]
            form.errors["answer_type"] = error
            return self.form_invalid(form)
        if not any(option.get("title") for option in data):
            error = [
                "At least one option should be supplied for (multiple) choice questions"
            ]
            form.errors["answer_type"] = error
            return self.form_invalid(form)
        with transaction.atomic():
            try:
                self.object = form.save()
            except Exception:
                return self.form_invalid(form)
            if options.is_valid():
                options.instance = self.object
                options.save()
        return _super.form_valid(form)


class QuestionUpdate(
    LoginRequiredMixin,
    QuestionOptionMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Question
    form_class = QuestionForm
    template_name = "reader_studies/readerstudy_update_object.html"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form_fields = context["form"].fields
        for field_name in self.object.read_only_fields:
            form_fields[field_name].required = False
            form_fields[field_name].disabled = True
        if self.request.POST:
            context["options"] = CategoricalOptionFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["options"] = CategoricalOptionFormSet(instance=self.object)
        context.update({"reader_study": self.reader_study})
        return context

    def form_valid(self, form):
        return self.validate_options(form, super())


class BaseAddObjectToReaderStudyMixin(
    LoginRequiredMixin, ObjectPermissionRequiredMixin
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
    raise_exception = True

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"object": self.reader_study, "type_to_add": self.type_to_add}
        )
        return context


class AddObjectToReaderStudyMixin(BaseAddObjectToReaderStudyMixin, CreateView):
    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.reader_study = self.reader_study
        return super().form_valid(form)


class AddGroundTruthToReaderStudy(BaseAddObjectToReaderStudyMixin, FormView):
    form_class = GroundTruthForm
    template_name = "reader_studies/readerstudy_add_object.html"
    type_to_add = "ground truth"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"reader_study": self.reader_study})
        return kwargs

    def form_valid(self, form):
        try:
            self.reader_study.add_ground_truth(
                data=form.cleaned_data["ground_truth"], user=self.request.user,
            )
            return super().form_valid(form)
        except ValidationError as e:
            form.errors["ground_truth"] = e
            return self.form_invalid(form)

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class ReaderStudyCopy(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, FormView
):
    form_class = ReaderStudyCopyForm
    template_name = "reader_studies/readerstudy_copy.html"
    # Note: these are explicitly checked in the check_permission function
    # and only left here for reference.
    permission_required = (
        f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}",
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}",
    )
    reader_study = None

    def get_permission_object(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def check_permissions(self, request):
        obj = self.get_permission_object()
        if not (
            request.user.has_perm(
                f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}"
            )
            and request.user.has_perm(
                f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}",
                obj,
            )
        ):
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"object": self.get_permission_object()})
        return context

    def form_valid(self, form):  # noqa: C901
        reader_study = self.get_permission_object()

        rs = ReaderStudy.objects.create(
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            **{
                field: getattr(reader_study, field)
                for field in ReaderStudy.copy_fields
            },
        )
        rs.add_editor(self.request.user)
        if form.cleaned_data["copy_images"]:
            rs.images.set(reader_study.images.all())
        if form.cleaned_data["copy_hanging_list"]:
            rs.hanging_list = reader_study.hanging_list
        if form.cleaned_data["copy_case_text"]:
            rs.case_text = reader_study.case_text
        if form.cleaned_data["copy_readers"]:
            for reader in reader_study.readers_group.user_set.all():
                rs.add_reader(reader)
        if form.cleaned_data["copy_editors"]:
            for editor in reader_study.editors_group.user_set.all():
                rs.add_editor(editor)
        if form.cleaned_data["copy_questions"]:
            for question in reader_study.questions.all():
                q = Question.objects.create(
                    reader_study=rs,
                    question_text=question.question_text,
                    help_text=question.help_text,
                    answer_type=question.answer_type,
                    image_port=question.image_port,
                    required=question.required,
                    direction=question.direction,
                    scoring_function=question.scoring_function,
                    order=question.order,
                )
                for option in question.options.all():
                    CategoricalOption.objects.create(
                        question=q, title=option.title, default=option.default
                    )
        rs.save()
        self.reader_study = rs
        return super().form_valid(form)

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class AddImagesToReaderStudy(AddObjectToReaderStudyMixin):
    model = RawImageUploadSession
    form_class = UploadRawImagesForm
    template_name = "reader_studies/readerstudy_add_object.html"
    type_to_add = "images"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "linked_task": add_images_to_reader_study.signature(
                    kwargs={"reader_study_pk": self.reader_study.pk},
                    immutable=True,
                ),
            }
        )
        return kwargs


class AddQuestionToReaderStudy(
    QuestionOptionMixin, AddObjectToReaderStudyMixin
):
    model = Question
    form_class = QuestionForm
    template_name = "reader_studies/readerstudy_add_object.html"
    type_to_add = "question"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["options"] = CategoricalOptionFormSet(self.request.POST)
        else:
            context["options"] = CategoricalOptionFormSet()
        context.update({"reader_study": self.reader_study})
        return context

    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.reader_study = self.reader_study
        return self.validate_options(form, super())


class ReaderStudyUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "reader_studies/readerstudy_user_groups_form.html"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )

    @property
    def obj(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])


class EditorsUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"


class ReadersUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = ReadersForm
    success_message = "Readers successfully updated"


class UsersProgress(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    template_name = "reader_studies/readerstudy_progress.html"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        users = [
            {
                "obj": reader,
                "progress": self.object.get_progress_for_user(reader),
            }
            for reader in get_user_model()
            .objects.filter(answer__question__reader_study=self.object)
            .distinct()
            .select_related("user_profile", "verification")
            .order_by("username")
        ]

        context.update({"reader_study": self.object, "users": users})

        return context


class AnswersRemove(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    template_name = "reader_studies/readerstudy_user_groups_form.html"
    form_class = AnswersRemoveForm
    success_message = "Answers removed"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def form_valid(self, form):
        form.remove_answers(reader_study=self.reader_study)
        return super().form_valid(form)

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class ReaderStudyPermissionRequestCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView
):
    model = ReaderStudyPermissionRequest
    fields = ()

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_success_url(self):
        return self.reader_study.get_absolute_url()

    def get_success_message(self, cleaned_data):
        return self.object.status_to_string()

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.reader_study = self.reader_study
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permission_request = ReaderStudyPermissionRequest.objects.filter(
            reader_study=self.reader_study, user=self.request.user
        ).first()
        context.update(
            {
                "permission_request": permission_request,
                "reader_study": self.reader_study,
            }
        )
        return context


class ReaderStudyPermissionRequestList(
    ObjectPermissionRequiredMixin, ListView
):
    model = ReaderStudyPermissionRequest
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.reader_study

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = (
            queryset.filter(reader_study=self.reader_study)
            .exclude(status=ReaderStudyPermissionRequest.ACCEPTED)
            .select_related("user__user_profile", "user__verification")
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"reader_study": self.reader_study})
        return context


class ReaderStudyPermissionRequestUpdate(PermissionRequestUpdate):
    model = ReaderStudyPermissionRequest
    form_class = ReaderStudyPermissionRequestUpdateForm
    base_model = ReaderStudy
    redirect_namespace = "reader-studies"
    user_check_attrs = ["is_reader", "is_editor"]
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"reader_study": self.base_object})
        return context


class ReaderStudyViewSet(ReadOnlyModelViewSet):
    serializer_class = ReaderStudySerializer
    queryset = ReaderStudy.objects.all().prefetch_related(
        "images", "questions__options"
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["slug"]
    change_permission = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    def _check_change_perms(self, user, obj):
        if not (user and user.has_perm(self.change_permission, obj)):
            raise Http404()

    @action(detail=True, methods=["patch"])
    def generate_hanging_list(self, request, pk=None):
        reader_study = self.get_object()
        reader_study.generate_hanging_list()
        messages.add_message(
            request, messages.SUCCESS, "Hanging list re-generated."
        )
        return Response({"status": "Hanging list generated."},)

    @action(detail=True, methods=["patch"])
    def remove_image(self, request, pk=None):
        image_id = request.data.get("image")
        reader_study = self.get_object()
        try:
            reader_study.images.remove(Image.objects.get(id=image_id))
            messages.add_message(
                request, messages.SUCCESS, "Image removed from reader study."
            )
            return Response({"status": "Image removed from reader study."},)
        except Image.DoesNotExist:
            messages.add_message(
                request,
                messages.ERROR,
                "Image could not be removed from reader study.",
            )
        return Response(
            {"status": "Image could not be removed from reader study."},
        )

    @action(detail=True, url_path="ground-truth/(?P<case_pk>[^/.]+)")
    def ground_truth(self, request, pk=None, case_pk=None):
        reader_study = self.get_object()
        if not (reader_study.is_educational and reader_study.has_ground_truth):
            raise Http404()
        try:
            image = reader_study.images.get(pk=case_pk)
        except Image.DoesNotExist:
            raise Http404()
        answers = Answer.objects.filter(
            images=image,
            question__reader_study=reader_study,
            is_ground_truth=True,
        )
        return JsonResponse(
            {
                str(answer.question_id): {
                    "answer": answer.answer,
                    "answer_text": answer.answer_text,
                    "question_text": answer.question.question_text,
                    "options": dict(
                        answer.question.options.values_list("id", "title")
                    ),
                    "explanation": answer.explanation,
                }
                for answer in answers
            }
        )


class QuestionViewSet(ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all().select_related("reader_study")
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["reader_study"]
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )


class AnswerViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = AnswerSerializer
    queryset = (
        Answer.objects.all()
        .select_related("creator", "question__reader_study")
        .prefetch_related("images")
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_class = AnswerFilter
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=False)
    def mine(self, request):
        """
        An endpoint that returns the questions that have been answered by
        the current user.
        """
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                creator=request.user, is_ground_truth=False
            )
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class QuestionDelete(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DeleteView
):
    model = Question

    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True

    success_message = "Question was successfully deleted"

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_success_url(self):
        return reverse(
            "reader-studies:detail", kwargs={"slug": self.kwargs["slug"]}
        )

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        if question.is_fully_editable:
            messages.success(self.request, self.success_message)
            return super().delete(request, *args, **kwargs)
        return HttpResponseForbidden(
            reason="This question already has answers associated with it"
        )
