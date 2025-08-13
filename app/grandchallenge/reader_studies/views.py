import csv
import logging

from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.forms import Form
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
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from guardian.core import ObjectPermissionChecker
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import get_perms
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from grandchallenge.archives.forms import AddCasesForm
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.views import (
    CIVSetBulkDelete,
    CIVSetDelete,
    CIVSetDetail,
    CIVSetFormMixin,
    CivSetListView,
    InterfacesCreateBaseView,
    MultipleCIVProcessingBaseView,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.utils import strtobool
from grandchallenge.core.utils.query import set_seed
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.filters import (
    AnswerFilter,
    ReaderStudyFilter,
)
from grandchallenge.reader_studies.forms import (
    AnswersFromGroundTruthForm,
    DisplaySetCreateForm,
    DisplaySetUpdateForm,
    GroundTruthCSVForm,
    GroundTruthFromAnswersForm,
    QuestionForm,
    ReadersForm,
    ReaderStudyCopyForm,
    ReaderStudyCreateForm,
    ReaderStudyPermissionRequestUpdateForm,
    ReaderStudyUpdateForm,
)
from grandchallenge.reader_studies.models import (
    Answer,
    CategoricalOption,
    DisplaySet,
    Question,
    ReaderStudy,
    ReaderStudyPermissionRequest,
)
from grandchallenge.reader_studies.serializers import (
    AnswerSerializer,
    DisplaySetPostSerializer,
    DisplaySetSerializer,
    QuestionSerializer,
    ReaderStudySerializer,
)
from grandchallenge.reader_studies.tasks import (
    copy_reader_study_display_sets,
    create_display_sets_for_upload_session,
)
from grandchallenge.subdomains.utils import reverse, reverse_lazy

logger = logging.getLogger(__name__)


class HttpResponseSeeOther(HttpResponseRedirect):
    status_code = 303


class ReaderStudyList(FilterMixin, ViewObjectPermissionListMixin, ListView):
    model = ReaderStudy
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
                    mark_safe(
                        random_encode("mailto:support@grand-challenge.org")
                    ),
                ),
            }
        )

        return context

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("optional_hanging_protocols")
        )


class ReaderStudyCreate(
    PermissionRequiredMixin, UserFormKwargsMixin, CreateView
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


class ReaderStudyGroundTruth(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True
    template_name = "reader_studies/readerstudy_ground_truth.html"


class ReaderStudyExampleGroundTruthCSV(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True

    def get(self, request, *args, **kwargs):
        reader_study = self.get_object()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="ground-truth-{reader_study.slug}.csv"'
        )
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
    permission_required = "reader_studies.view_readerstudy"
    raise_exception = True
    queryset = ReaderStudy.objects.prefetch_related(
        "optional_hanging_protocols"
    )

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

            pending_permission_requests = (
                ReaderStudyPermissionRequest.objects.filter(
                    reader_study=context["object"],
                    status=ReaderStudyPermissionRequest.PENDING,
                ).count()
            )

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
                    * self.object.display_sets.count(),
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
            "display_set_offsets": range(
                0, self.object.display_sets.count(), limit
            ),
            "image_offsets": range(
                0,
                Image.objects.filter(
                    componentinterfacevalue__display_sets__reader_study=self.object
                )
                .distinct()
                .count(),
                limit,
            ),
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
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True
    success_message = "Reader study successfully updated"


class ReaderStudyDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = ReaderStudy
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True
    success_message = "Reader study was successfully deleted"

    def get_success_url(self):
        return reverse("reader-studies:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        nested_objects = NestedObjects(using="default")
        nested_objects.collect([self.object])
        context.update({"nested_objects": nested_objects})

        return context


class ReaderStudyLeaderBoard(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    template_name = "reader_studies/readerstudy_leaderboard.html"
    permission_required = "reader_studies.view_leaderboard"
    raise_exception = True


class ReaderStudyStatistics(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True
    template_name = "reader_studies/readerstudy_statistics.html"
    # TODO: this view also contains the ground truth answer values.
    # If the permission is changed to 'read', we need to filter these values out.


class ReaderStudyDisplaySetList(ObjectPermissionRequiredMixin, CivSetListView):
    model = DisplaySet
    permission_required = (
        "reader_studies.change_readerstudy"  # so that readers don't get access
    )
    raise_exception = True

    default_sort_column = 4

    search_fields = [
        "order",
        *CivSetListView.search_fields,
    ]

    @property
    def columns(self):
        columns = CivSetListView.columns.copy()
        columns.insert(
            4,
            Column(title="Order", sort_field="order"),
        )
        return columns

    @cached_property
    def base_object(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.base_object

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        if Answer.objects.filter(
            question__reader_study=self.base_object
        ).exists():
            context["delete_all_disabled_message"] = (
                "Cannot delete all display sets: first you need to delete all of the answers for this reader study"
            )

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        return (
            queryset.filter(reader_study=self.base_object)
            .select_related("reader_study")
            .prefetch_related("answers")
        )


class QuestionUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Question
    form_class = QuestionForm
    template_name = "reader_studies/readerstudy_update_object.html"
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True

    def get_permission_object(self):
        return self.get_object().reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"reader_study": self.reader_study, "user": self.request.user}
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"reader_study": self.reader_study})
        return context


class BaseAddObjectToReaderStudyMixin(
    LoginRequiredMixin, ObjectPermissionRequiredMixin
):
    """
    Mixin that adds an object that has a foreign key to a reader study and a
    creator. The url to this view must include a slug that points to the slug
    of the reader study.
    """

    permission_required = "reader_studies.change_readerstudy"
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


class AddGroundTruthViaCSVToReaderStudy(
    SuccessMessageMixin, BaseAddObjectToReaderStudyMixin, FormView
):
    form_class = GroundTruthCSVForm
    template_name = "reader_studies/ground_truth_csv_form.html"
    type_to_add = "Ground Truth"
    success_message = "Ground Truth has been added succesfully. Updating the scores is done asynchronously."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "reader_study": self.reader_study,
            }
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "example_ground_truth": self.reader_study.get_example_ground_truth_csv_text(
                    limit=2
                )
            }
        )
        return context

    def form_valid(self, form):
        form.save_answers()
        return super().form_valid(form)

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class ReaderStudyGroundTruthFromAnswers(
    SuccessMessageMixin,
    BaseAddObjectToReaderStudyMixin,
    FormView,
):
    form_class = GroundTruthFromAnswersForm
    template_name = "reader_studies/ground_truth_from_answers_form.html"
    type_to_add = "Ground Truth"
    success_message = "Answers have been succesfully converted to Ground Truth. Updating the scores is done asynchronously."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"reader_study": self.reader_study})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        form.create_ground_truth()
        return response

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class ReaderStudyAnswersFromGroundTruth(
    SuccessMessageMixin,
    BaseAddObjectToReaderStudyMixin,
    FormView,
):
    form_class = AnswersFromGroundTruthForm
    template_name = "reader_studies/answers_from_ground_truth_form.html"
    type_to_add = "Answers"
    success_message = (
        "Copying of Ground Truth to Answers will be done asynchronously."
    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "reader_study": self.reader_study,
                "request_user": self.request.user,
            }
        )
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        form.schedule_answers_from_ground_truth_task()
        return response

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
        "reader_studies.add_readerstudy",
        "reader_studies.change_readerstudy",
    )
    reader_study = None

    def get_permission_object(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def check_permissions(self, request):
        obj = self.get_permission_object()
        if not (
            request.user.has_perm("reader_studies.add_readerstudy")
            and request.user.has_perm("reader_studies.change_readerstudy", obj)
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

        if form.cleaned_data["copy_view_content"]:
            rs.view_content = reader_study.view_content
        if form.cleaned_data["copy_hanging_protocol"]:
            rs.hanging_protocol = reader_study.hanging_protocol
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
                    default_annotation_color=question.default_annotation_color,
                    required=question.required,
                    direction=question.direction,
                    scoring_function=question.scoring_function,
                    order=question.order,
                    interface=question.interface,
                    look_up_table=question.look_up_table,
                    overlay_segments=question.overlay_segments,
                    widget=question.widget,
                    interactive_algorithm=question.interactive_algorithm,
                    answer_max_value=question.answer_max_value,
                    answer_min_value=question.answer_min_value,
                    answer_step_size=question.answer_step_size,
                    answer_min_length=question.answer_min_length,
                    answer_max_length=question.answer_max_length,
                    answer_match_pattern=question.answer_match_pattern,
                    empty_answer_confirmation=question.empty_answer_confirmation,
                    empty_answer_confirmation_label=question.empty_answer_confirmation_label,
                )
                for option in question.options.all():
                    CategoricalOption.objects.create(
                        question=q, title=option.title, default=option.default
                    )
        rs.save()
        self.reader_study = rs
        if form.cleaned_data["copy_display_sets"]:
            transaction.on_commit(
                lambda: copy_reader_study_display_sets.apply_async(
                    kwargs={
                        "orig_pk": str(reader_study.pk),
                        "new_pk": str(rs.pk),
                    }
                )
            )
            messages.add_message(
                self.request,
                messages.INFO,
                "Display sets will be copied asynchronously.",
            )
        return super().form_valid(form)

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class AddDisplaySetsToReaderStudy(BaseAddObjectToReaderStudyMixin, CreateView):
    model = RawImageUploadSession
    form_class = AddCasesForm
    template_name = "reader_studies/readerstudy_add_object.html"
    type_to_add = "images"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "linked_task": create_display_sets_for_upload_session.signature(
                    kwargs={"reader_study_pk": self.reader_study.pk},
                    immutable=True,
                ),
                "interface_viewname": "components:component-interface-list-reader-studies",
            }
        )
        return kwargs

    def form_valid(self, form):
        # TODO this should be set in the form
        form.instance.creator = self.request.user
        return super().form_valid(form)


class AddQuestionToReaderStudy(BaseAddObjectToReaderStudyMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = "reader_studies/readerstudy_add_object.html"
    type_to_add = "question"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {"reader_study": self.reader_study, "user": self.request.user}
        )
        return kwargs


class ReaderStudyUserGroupUpdateMixin(UserGroupUpdateMixin):
    template_name = "reader_studies/readerstudy_user_groups_form.html"
    permission_required = "reader_studies.change_readerstudy"

    @property
    def obj(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])


class EditorsUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = EditorsForm
    success_message = "Editors successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#editors"


class ReadersUpdate(ReaderStudyUserGroupUpdateMixin):
    form_class = ReadersForm
    success_message = "Readers successfully updated"

    def get_success_url(self):
        url = super().get_success_url()
        return f"{url}#readers"


class UsersProgress(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    template_name = "reader_studies/readerstudy_progress.html"
    permission_required = "reader_studies.change_readerstudy"
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

        context.update(
            {
                "reader_study": self.object,
                "users": users,
            }
        )

        return context


class AnswerBatchDelete(LoginRequiredMixin, FormView):
    permission_required = "reader_studies.delete_answer"
    raise_exception = True
    success_message = "Answers removed"
    form_class = Form

    def check_permissions(self, request):
        permission_objects = self.get_queryset()
        checker = ObjectPermissionChecker(request.user)
        checker.prefetch_perms(permission_objects)
        forbidden = any(
            not checker.has_perm(self.permission_required, obj)
            for obj in permission_objects
        )
        if forbidden:
            raise PermissionDenied()
        return permission_objects

    def get_queryset(self):
        raise NotImplementedError

    def form_valid(self, *args, **kwargs):
        objects = self.check_permissions(self.request)
        objects.delete()

        messages.success(self.request, self.success_message)

        return HttpResponse(
            self.get_success_url(),
            headers={
                "HX-Redirect": self.get_success_url(),
                "HX-Refresh": True,
            },
        )

    @cached_property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_success_url(self):
        return self.reader_study.get_absolute_url()


class AnswersRemoveForUser(AnswerBatchDelete):
    def get_queryset(self):
        return Answer.objects.filter(
            question__reader_study=self.reader_study,
            creator__username=self.kwargs["username"],
            is_ground_truth=False,
        )

    def get_success_url(self):
        return reverse(
            "reader-studies:users-progress",
            kwargs={"slug": self.kwargs["slug"]},
        )


class ReaderStudyGroundTruthDelete(AnswerBatchDelete):
    template_name = "reader_studies/ground_truth_confirm_delete.html"
    success_message = "Ground truth successfully deleted"

    def get_success_url(self):
        return reverse(
            "reader-studies:ground-truth",
            kwargs={"slug": self.reader_study.slug},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.reader_study
        return context

    def get_queryset(self):
        return Answer.objects.filter(
            question__reader_study=self.reader_study,
            is_ground_truth=True,
        )

    def form_valid(self, *args, **kwargs):
        Answer.objects.filter(question__reader_study=self.reader_study).update(
            score=None
        )
        return super().form_valid()


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
            form.add_error(None, ErrorList(e.messages))
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
    permission_required = "reader_studies.change_readerstudy"
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
    permission_required = "reader_studies.change_readerstudy"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"reader_study": self.base_object})
        return context


class ReaderStudyViewSet(ReadOnlyModelViewSet):
    serializer_class = ReaderStudySerializer
    queryset = ReaderStudy.objects.all().prefetch_related(
        "questions__options",
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "case_pk", OpenApiTypes.UUID, OpenApiParameter.PATH
            ),
        ],
    )
    @action(detail=True, url_path="ground-truth/(?P<case_pk>[^/.]+)")
    def ground_truth(self, request, pk=None, case_pk=None):
        reader_study = self.get_object()
        if not (reader_study.is_educational and reader_study.has_ground_truth):
            raise Http404()
        answers = Answer.objects.filter(
            display_set_id=case_pk,
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


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "unanswered_by_user", OpenApiTypes.BOOL, OpenApiParameter.QUERY
            ),
            OpenApiParameter("user", OpenApiTypes.STR, OpenApiParameter.QUERY),
        ],
    ),
)
class DisplaySetViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = DisplaySetSerializer
    queryset = (
        DisplaySet.objects.all()
        .select_related("reader_study__hanging_protocol")
        .prefetch_related(
            "values__image",
            "values__interface",
            "reader_study__display_sets",
            "reader_study__optional_hanging_protocols",
        )
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
    filterset_fields = ["reader_study"]
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )
    randomized_qs = []

    @property
    def reader_study(self):
        reader_study_pk = self.request.query_params.get("reader_study")
        if reader_study_pk:
            return ReaderStudy.objects.get(pk=reader_study_pk)

    def get_serializer_class(self):
        if self.action in ["partial_update", "update", "create"]:
            return DisplaySetPostSerializer
        return DisplaySetSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        # Note: if more fields besides 'reader_study' are added to the
        # filter_set fields, we cannot call super anymore before randomizing
        # as we only want to filter out the display sets for a specific
        # reader study.
        reader_study = self.reader_study
        if reader_study and reader_study.shuffle_hanging_list:
            queryset = queryset.filter(reader_study=reader_study)
            queryset = self.create_randomized_qs(queryset=queryset)
        unanswered_by_user = strtobool(
            self.request.query_params.get("unanswered_by_user", "False")
        )
        username = self.request.query_params.get("user", False)

        if username and not unanswered_by_user:
            raise DRFValidationError(
                "Specifying a user is only possible when retrieving unanswered"
                " display sets."
            )
        if username:
            user = get_user_model().objects.filter(username=username).get()
            if user != self.request.user and not self.request.user.has_perm(
                "change_readerstudy", self.reader_study
            ):
                raise PermissionDenied(
                    "You do not have permission to retrieve this user's unanswered"
                    " display sets."
                )
        else:
            user = self.request.user

        if unanswered_by_user is True:
            if reader_study is None:
                raise DRFValidationError(
                    "Please provide a reader study when filtering for "
                    "unanswered display_sets."
                )
            answerable_question_count = reader_study.answerable_question_count
            queryset = (
                queryset.annotate(
                    answer_count=Count(
                        "answers",
                        filter=Q(
                            answers__is_ground_truth=False,
                            answers__creator=user,
                        ),
                    )
                )
                .exclude(
                    answer_count__gte=answerable_question_count,
                )
                .order_by("order", "created")
            )
            # Because the filtering has changed the list, we can no longer
            # reapply .order_by("?"), as the ordering would not be consistent
            # with the ordering of the full list. Instead, we use the
            # previously saved randomized_qs and filter the proper items
            # out of it.
            if reader_study and reader_study.shuffle_hanging_list:
                pks = queryset.values_list("pk", flat=True)
                queryset = [x for x in self.randomized_qs if x.pk in pks]

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_object(self):
        obj = super().get_object()
        # retrieve the full queryset and save its shuffled version to later
        # determine the shuffled index for this object
        if obj.reader_study.shuffle_hanging_list:
            queryset = self.get_queryset()
            queryset = super().filter_queryset(queryset)
            queryset = queryset.filter(reader_study=obj.reader_study)
            self.create_randomized_qs(queryset=queryset)
        return obj

    def create_randomized_qs(self, queryset):
        set_seed(1 / int(self.request.user.pk))
        queryset = queryset.order_by("?")
        # Save the queryset to determine each item's index in the serializer
        self.randomized_qs = list(queryset)
        return queryset


class QuestionViewSet(ReadOnlyModelViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all().select_related("reader_study")
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
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
    queryset = Answer.objects.all().select_related(
        "creator",
        "question__reader_study",
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ViewObjectPermissionsFilter]
    filterset_class = AnswerFilter
    renderer_classes = (
        *api_settings.DEFAULT_RENDERER_CLASSES,
        PaginatedCSVRenderer,
    )

    def perform_create(self, serializer):
        last_edit_duration = serializer.validated_data.get(
            "last_edit_duration"
        )
        serializer.save(
            creator=self.request.user, total_edit_duration=last_edit_duration
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        last_edit_duration = serializer.validated_data.get(
            "last_edit_duration"
        )
        total_edit_duration = None
        if (
            instance.total_edit_duration is not None
            and last_edit_duration is not None
        ):
            total_edit_duration = (
                instance.total_edit_duration + last_edit_duration
            )

        serializer.save(total_edit_duration=total_edit_duration)

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
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = Question
    permission_required = "reader_studies.change_readerstudy"
    raise_exception = True
    success_message = "Question was successfully deleted"

    def get_permission_object(self):
        return self.get_object().reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def get_success_url(self):
        url = reverse(
            "reader-studies:detail", kwargs={"slug": self.kwargs["slug"]}
        )
        return f"{url}#questions"

    def form_valid(self, *args, **kwargs):
        question = self.get_object()
        if question.is_fully_editable:
            return super().form_valid(*args, **kwargs)
        else:
            return HttpResponseForbidden(
                reason="This question already has answers associated with it"
            )


class QuestionInterfacesView(BaseAddObjectToReaderStudyMixin, View):
    def get(self, request, slug):
        form = QuestionForm(
            request.GET, reader_study=self.reader_study, user=self.request.user
        )
        return HttpResponse(form["interface"])


class QuestionWidgetsView(BaseAddObjectToReaderStudyMixin, View):
    def get(self, request, slug):
        form = QuestionForm(
            request.GET, reader_study=self.reader_study, user=self.request.user
        )
        return HttpResponse(form["widget"])


class QuestionInteractiveAlgorithmsView(
    UserPassesTestMixin, BaseAddObjectToReaderStudyMixin, View
):
    def test_func(self):
        return self.request.user.has_perm(
            "reader_studies.add_interactive_algorithm_to_question"
        )

    def get(self, request, slug):
        form = QuestionForm(
            request.GET, reader_study=self.reader_study, user=self.request.user
        )
        return HttpResponse(form["interactive_algorithm"])


class DisplaySetDetailView(CIVSetDetail):
    model = DisplaySet
    permission_required = "reader_studies.view_displayset"


class DisplaySetUpdateView(
    CIVSetFormMixin,
    MultipleCIVProcessingBaseView,
):
    form_class = DisplaySetUpdateForm
    permission_required = "reader_studies.change_displayset"
    included_form_classes = (
        DisplaySetUpdateForm,
        *MultipleCIVProcessingBaseView.included_form_classes,
    )
    success_message = "Display set has been updated."

    def get_permission_object(self):
        return self.object

    @property
    def object(self):
        return DisplaySet.objects.get(pk=self.kwargs["pk"])

    @property
    def base_object(self):
        return self.object.base_object

    def get_success_url(self):
        return self.return_url

    @property
    def form_url(self):
        return reverse(
            "reader-studies:display-set-update",
            kwargs={"slug": self.base_object.slug, "pk": self.object.pk},
        )

    @property
    def return_url(self):
        return reverse(
            "reader-studies:display_sets",
            kwargs={"slug": self.base_object.slug},
        )

    @property
    def new_interface_url(self):
        return reverse(
            "reader-studies:display-set-interfaces-create",
            kwargs={"slug": self.base_object.slug, "pk": self.object.pk},
        )


class DisplaySetInterfacesCreate(InterfacesCreateBaseView):
    def get_required_permissions(self, request):
        if self.object:
            return [
                f"{ReaderStudy._meta.app_label}.change_{DisplaySet._meta.model_name}"
            ]
        else:
            return [
                f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
            ]

    @property
    def object(self):
        if self.kwargs.get("pk"):
            return DisplaySet.objects.get(pk=self.kwargs["pk"])
        else:
            return None

    @property
    def base_object(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_htmx_url(self):
        if self.kwargs.get("pk") is not None:
            return reverse_lazy(
                "reader-studies:display-set-interfaces-create",
                kwargs={
                    "pk": self.kwargs.get("pk"),
                    "slug": self.base_object.slug,
                },
            )
        else:
            return reverse_lazy(
                "reader-studies:display-set-new-interfaces-create",
                kwargs={"slug": self.base_object.slug},
            )


class DisplaySetCreate(
    CIVSetFormMixin,
    MultipleCIVProcessingBaseView,
):
    form_class = DisplaySetCreateForm
    permission_required = "reader_studies.change_readerstudy"
    included_form_classes = (
        DisplaySetCreateForm,
        *MultipleCIVProcessingBaseView.included_form_classes,
    )
    success_message = "Display set has been created."

    def get_permission_object(self):
        return self.base_object

    @property
    def base_object(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    @property
    def form_url(self):
        return reverse(
            "reader-studies:display-set-create",
            kwargs={"slug": self.base_object.slug},
        )

    @property
    def return_url(self):
        return reverse(
            "reader-studies:display_sets",
            kwargs={"slug": self.base_object.slug},
        )

    @property
    def new_interface_url(self):
        return reverse(
            "reader-studies:display-set-new-interfaces-create",
            kwargs={"slug": self.base_object.slug},
        )

    def get_success_url(self):
        return self.return_url


class DisplaySetDelete(CIVSetDelete):
    model = DisplaySet
    permission_required = "reader_studies.delete_displayset"


class DisplaySetBulkDelete(CIVSetBulkDelete):
    model = DisplaySet

    @property
    def base_object(self):
        return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset()
        return self.base_object.civ_sets_related_manager.filter(
            pk__in=[ds.pk for ds in qs if ds.is_editable]
        )
