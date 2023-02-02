import csv
import json
import uuid

from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.db.transaction import on_commit
from django.forms import Media
from django.forms.utils import ErrorList
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
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
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.archives.forms import AddCasesForm
from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)
from grandchallenge.components.serializers import (
    ComponentInterfaceValuePostSerializer,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.core.renderers import PaginatedCSVRenderer
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.utils import strtobool
from grandchallenge.core.utils.query import set_seed
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.groups.forms import EditorsForm
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.reader_studies.filters import (
    AnswerFilter,
    ReaderStudyFilter,
)
from grandchallenge.reader_studies.forms import (
    CategoricalOptionFormSet,
    DisplaySetCreateForm,
    DisplaySetInterfacesCreateForm,
    DisplaySetUpdateForm,
    FileForm,
    GroundTruthForm,
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
    add_file_to_display_set,
    add_image_to_display_set,
    copy_reader_study_display_sets,
    create_display_sets_for_upload_session,
)
from grandchallenge.subdomains.utils import reverse


class HttpResponseSeeOther(HttpResponseRedirect):
    status_code = 303


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
                    mark_safe(
                        random_encode("mailto:support@grand-challenge.org")
                    ),
                ),
            }
        )

        return context


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


class ReaderStudyDisplaySetList(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, PaginatedTableListView
):
    model = DisplaySet
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    template_name = "reader_studies/readerstudy_images_list.html"
    row_template = "reader_studies/readerstudy_display_sets_row.html"
    search_fields = ["pk", "values__image__name", "values__file"]
    columns = [
        Column(title="[DisplaySet ID] Main image name", sort_field="order"),
    ]
    text_align = "left"
    default_sort_order = "asc"
    included_form_classes = (
        DisplaySetUpdateForm,
        DisplaySetInterfacesCreateForm,
        FileForm,
    )

    @cached_property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

    def render_row(self, *, object_, page_context):
        return render_to_string(
            self.row_template,
            context={**page_context, "object": object_},
        ).split("<split></split>")

    def get_permission_object(self):
        return self.reader_study

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        media = Media()
        for form_class in self.included_form_classes:
            for widget in form_class._possible_widgets:
                media = media + widget().media

        context.update(
            {
                "form_media": media,
                "reader_study": self.reader_study,
            }
        )
        return context

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(reader_study=self.reader_study)
            .select_related("reader_study")
            .prefetch_related(
                "values", "answers", "values__image", "values__interface"
            )
            .order_by()
            .distinct()
        )
        return qs


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
        Column(title="View"),
        Column(title="Download"),
        Column(title="Remove from Study"),
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
            .prefetch_related("files")
            .select_related(
                "origin__creator__user_profile",
                "origin__creator__verification",
            )
        )


class QuestionOptionMixin:
    def validate_options(self, form, _super):
        context = self.get_context_data()
        options = context["options"]
        if form.cleaned_data["answer_type"] not in [
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
                data=form.cleaned_data["ground_truth"], user=self.request.user
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


class AddDisplaySetsToReaderStudy(AddObjectToReaderStudyMixin):
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

        context.update(
            {
                "reader_study": self.object,
                "users": users,
            }
        )

        return context


class AnswerBatchDelete(LoginRequiredMixin, DeleteView):
    permission_required = (
        f"{Answer._meta.app_label}.delete_{Answer._meta.model_name}"
    )
    raise_exception = True
    success_message = "Answers removed"

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

    def delete(self, request, *args, **kwargs):
        objects = self.check_permissions(request)
        objects.delete()
        messages.add_message(request, messages.SUCCESS, self.success_message)
        return HttpResponse(
            self.get_success_url(),
            headers={
                "HX-Redirect": self.get_success_url(),
                "HX-Refresh": True,
            },
        )

    @property
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


class AnswersRemoveGroundTruth(AnswerBatchDelete):
    success_message = "Ground truth removed"

    def get_queryset(self):
        return Answer.objects.filter(
            question__reader_study=self.reader_study,
            is_ground_truth=True,
        )


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
        "questions__options",
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
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    serializer_class = DisplaySetSerializer
    queryset = (
        DisplaySet.objects.all()
        .select_related("reader_study__hanging_protocol")
        .prefetch_related(
            "values__image", "values__interface", "reader_study__display_sets"
        )
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
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

    def create_civ(self, data):
        interface = data.pop("interface", None)
        value = data.pop("value", None)
        image = data.pop("image", None)

        if (interface.is_image_kind and image) or interface.is_json_kind:
            with transaction.atomic():
                return interface.create_instance(image=image, value=value)
        else:
            raise DRFValidationError(
                f"No image, file or value provided for {interface.title}."
            )

    def partial_update(self, request, pk=None):
        instance = self.get_object()
        if not instance.is_editable:
            return HttpResponseBadRequest(
                "This display set cannot be changed, "
                "as answers for it already exist."
            )
        assigned_civs = []
        values = request.data.pop("values", None)
        civs = instance.reader_study.display_sets.values_list(
            "values", flat=True
        )
        assigned_civs = []
        if values:
            serialized_data = ComponentInterfaceValuePostSerializer(
                many=True, data=values, context={"request": request}
            )
            if serialized_data.is_valid():
                civs = []
                interfaces = []
                for value in serialized_data.validated_data:
                    interface = value.get("interface", None)
                    user_upload = value.get("user_upload", None)
                    if interface.requires_file and user_upload:
                        interfaces.append(interface)
                        transaction.on_commit(
                            add_file_to_display_set.signature(
                                kwargs={
                                    "user_upload_pk": str(user_upload.pk),
                                    "interface_pk": str(interface.pk),
                                    "display_set_pk": str(instance.pk),
                                }
                            ).apply_async
                        )
                    else:
                        civs.append(self.create_civ(value))
                civs = [x for x in civs if x]
                assigned_civs = instance.values.filter(
                    interface__in=[civ.interface for civ in civs]
                )
                instance.values.remove(*assigned_civs)
                instance.values.add(*civs)

        # Create a new display set for any civs that have been replaced by a
        # new value in this display set, to ensure it remains connected to
        # the reader study.
        for assigned in assigned_civs:
            if not instance.reader_study.display_sets.filter(
                values=assigned
            ).exists():
                ds = DisplaySet.objects.create(
                    reader_study=instance.reader_study
                )
                ds.values.add(assigned)
            instance.values.remove(assigned)
        return super().partial_update(request, pk)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_editable:
            raise PermissionDenied(
                "This display set cannot be removed, as answers for it "
                "already exist."
            )
        return super().destroy(request, *args, **kwargs)

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
    queryset = Answer.objects.all().select_related(
        "creator",
        "question__reader_study",
    )
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
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
        url = reverse(
            "reader-studies:detail", kwargs={"slug": self.kwargs["slug"]}
        )
        return f"{url}#questions"

    def delete(self, request, *args, **kwargs):
        question = self.get_object()
        if question.is_fully_editable:
            messages.success(self.request, self.success_message)
            return super().delete(request, *args, **kwargs)
        return HttpResponseForbidden(
            reason="This question already has answers associated with it"
        )


class QuestionInterfacesView(View):
    def get(self, request):
        form = QuestionForm(request.GET)
        return HttpResponse(form["interface"])


class DisplaySetDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    template_name = "reader_studies/display_set_detail.html"
    model = DisplaySet
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{DisplaySet._meta.model_name}"
    )
    raise_exception = True


class DisplaySetUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    template_name = "reader_studies/display_set_update.html"
    model = DisplaySet
    form_class = DisplaySetUpdateForm
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{DisplaySet._meta.model_name}"
    )
    raise_exception = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "auto_id": f"id-{self.kwargs['pk']}-%s",
                "reader_study": self.object.reader_study,
            }
        )
        return kwargs

    def get_success_url(self):
        return reverse(
            "reader-studies:display-set-detail",
            kwargs={"pk": self.kwargs["pk"], "slug": self.kwargs["slug"]},
        )

    def form_valid(self, form):
        """Handles the update action on the object.

        The reason this is handled here and not in the form class is that we
        do not use a ModelForm for display sets. This is because the form
        fields do not match the model fields: the model only has a `values`
        fields, whereas the form has a field for each value in those values.
        """
        instance = self.get_object()
        assigned_civs = []
        for ci_slug, new_value in form.cleaned_data.items():
            if ci_slug == "order" or new_value is None:
                continue
            instance, assigned_civs = self.create_civ_for_value(
                instance=instance,
                ci_slug=ci_slug,
                new_value=new_value,
                assigned_civs=assigned_civs,
            )
        instance.values.remove(*assigned_civs)

        if (
            form.cleaned_data.get("order")
            and form.cleaned_data["order"] != instance.order
        ):
            instance.order = form.cleaned_data["order"]
            instance.save()

        return HttpResponseRedirect(self.get_success_url())

    def create_civ_for_value(
        self, instance, ci_slug, new_value, assigned_civs
    ):
        ci = ComponentInterface.objects.get(slug=ci_slug)
        current_value = instance.values.filter(interface=ci).first()
        if ci.is_json_kind and not ci.requires_file:
            if current_value:
                assigned_civs.append(current_value)
            val = ComponentInterfaceValue.objects.create(
                interface=ci, value=new_value
            )
            instance.values.add(val)
        elif isinstance(new_value, Image):
            if not current_value or (
                current_value and current_value.image != new_value
            ):
                assigned_civs.append(current_value)
                civ, created = ComponentInterfaceValue.objects.get_or_create(
                    interface=ci, image=new_value
                )
                if created:
                    civ.full_clean()
                instance.values.add(civ)
        elif isinstance(new_value, QuerySet):
            us = RawImageUploadSession.objects.create(
                creator=self.request.user,
            )
            us.user_uploads.set(new_value)
            us.process_images(
                linked_task=add_image_to_display_set.signature(
                    kwargs={
                        "display_set_pk": instance.pk,
                        "interface_pk": str(ci.pk),
                    },
                    immutable=True,
                )
            )
        else:
            if current_value:
                assigned_civs.append(current_value)
            # If there is already a value for the provided civ's interface in
            # this display set, remove it from this display set. Cast to list
            # to evaluate immediately.
            assigned_civs += list(
                instance.values.exclude(pk=new_value.pk).filter(interface=ci)
            )
            # Add the provided civ to the current display set
            instance.values.add(new_value)
        return instance, assigned_civs


class DisplaySetFilesUpdate(ObjectPermissionRequiredMixin, FormView):
    form_class = FileForm
    template_name = "reader_studies/display_set_files_update.html"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{DisplaySet._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.display_set

    @cached_property
    def interface(self):
        return ComponentInterface.objects.get(
            slug=self.kwargs["interface_slug"]
        )

    @cached_property
    def display_set(self):
        return DisplaySet.objects.get(pk=self.kwargs["pk"])

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "display_set": self.kwargs["pk"],
                "interface": self.kwargs["interface_slug"],
                "slug": self.kwargs["slug"],
            }
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "display_set": self.display_set,
                "interface": self.interface,
                "auto_id": f"id-{self.kwargs['pk']}-%s",
            }
        )
        return kwargs

    def form_valid(self, form):
        try:
            civ = self.display_set.values.get(interface=self.interface)
        except ObjectDoesNotExist:
            civ = None
        user_upload = form.cleaned_data["user_upload"]
        on_commit(
            lambda: add_file_to_display_set.apply_async(
                kwargs={
                    "user_upload_pk": str(user_upload.pk),
                    "interface_pk": str(self.interface.pk),
                    "display_set_pk": str(self.display_set.pk),
                    "civ_pk": str(civ.pk) if civ else None,
                }
            )
        )
        messages.add_message(
            self.request, messages.SUCCESS, "File import started."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "reader-studies:display-set-detail",
            kwargs={"pk": self.kwargs["pk"], "slug": self.kwargs["slug"]},
        )


class DisplaySetInterfacesCreate(ObjectPermissionRequiredMixin, FormView):
    form_class = DisplaySetInterfacesCreateForm
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{DisplaySet._meta.model_name}"
    )
    raise_exception = True

    def get_permission_object(self):
        return self.display_set

    @property
    def display_set(self):
        if self.kwargs.get("pk"):
            return DisplaySet.objects.get(pk=self.kwargs["pk"])

    @property
    def reader_study(self):
        if self.display_set:
            return self.display_set.reader_study
        else:
            return ReaderStudy.objects.get(slug=self.kwargs["slug"])

    def get_template_names(self):
        if self.kwargs.get("pk"):
            return ["reader_studies/display_set_interface_create.html"]
        else:
            return ["reader_studies/display_set_new_interface_create.html"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "pk": self.kwargs.get("pk"),
                "reader_study": self.reader_study,
                "interface": self.request.GET.get("interface"),
                "user": self.request.user,
                "auto_id": f"id-{uuid.uuid4()}-%s",
            }
        )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({"object": self.display_set})
        return context

    def update_display_set(self, interface, value):
        if interface.is_image_kind:
            if isinstance(value, Image):
                civ, created = ComponentInterfaceValue.objects.get_or_create(
                    interface=interface, image=value
                )
                if created:
                    civ.full_clean()
                self.display_set.values.add(civ)
            else:
                us = RawImageUploadSession.objects.create(
                    creator=self.request.user,
                )
                us.user_uploads.set(value)
                us.process_images(
                    linked_task=add_image_to_display_set.signature(
                        kwargs={
                            "display_set_pk": self.kwargs["pk"],
                            "interface_pk": str(interface.pk),
                        },
                        immutable=True,
                    )
                )
                messages.add_message(
                    self.request, messages.SUCCESS, "Image import queued."
                )
        elif interface.requires_file:
            transaction.on_commit(
                add_file_to_display_set.signature(
                    kwargs={
                        "user_upload_pk": str(value.pk),
                        "interface_pk": str(interface.pk),
                        "display_set_pk": self.kwargs["pk"],
                    }
                ).apply_async
            )

            messages.add_message(
                self.request, messages.SUCCESS, "File copy queued."
            )
        else:
            civ = interface.create_instance(value=value)
            self.display_set.values.add(civ)

    def form_valid(self, form):
        interface = form.cleaned_data["interface"]
        value = form.cleaned_data[interface.slug]
        if self.display_set:
            try:
                self.update_display_set(interface, value)
            except ValidationError as e:
                form.add_error(interface.slug, str(e))
                return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "reader-studies:display-set-update",
            kwargs={"pk": self.kwargs["pk"], "slug": self.kwargs["slug"]},
        )


class AddDisplaySetToReaderStudy(
    AddObjectToReaderStudyMixin, ObjectPermissionRequiredMixin, CreateView
):
    model = DisplaySet
    form_class = DisplaySetCreateForm
    template_name = "reader_studies/display_set_create.html"
    type_to_add = "case"
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    included_form_classes = (
        DisplaySetCreateForm,
        DisplaySetInterfacesCreateForm,
    )

    def get_permission_object(self):
        return self.reader_study

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "reader_study": self.reader_study,
                "user": self.request.user,
                "instance": None,
            }
        )
        if self.request.method in ("POST", "PUT"):
            data = json.loads(self.request.body)
            for key in data:
                if (
                    key
                    in [
                        "order",
                        "csrfmiddlewaretoken",
                        "new_interfaces",
                        "help_text",
                        "current_value",
                        "interface_slug",
                    ]
                    or "WidgetChoice" in key
                    or "query" in key
                ):
                    continue
                interface = ComponentInterface.objects.get(slug=key)
                if interface.is_image_kind:
                    data[key] = data[key]
            kwargs.update(
                {
                    "data": data,
                }
            )
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        media = Media()
        for form_class in self.included_form_classes:
            for widget in form_class._possible_widgets:
                media = media + widget().media
        context.update(
            {
                "reader_study": self.reader_study,
                "form_media": media,
            }
        )
        return context

    def _process_new_interfaces(self):
        data = json.loads(self.request.body)
        new_interfaces = data["new_interfaces"]
        validated_data = {}
        errors = {}
        for entry in new_interfaces:
            interface = ComponentInterface.objects.get(pk=entry["interface"])
            form = DisplaySetInterfacesCreateForm(
                data=entry,
                pk=None,
                interface=interface.pk,
                user=self.request.user,
                reader_study=self.reader_study,
                auto_id="%s",
            )
            if form.is_valid():
                cleaned = form.cleaned_data
                validated_data[cleaned["interface"].slug] = cleaned[
                    interface.slug
                ]
            else:
                errors.update(
                    {entry["interface"]: form.errors[interface.slug]}
                )
        if errors:
            raise ValidationError(errors)
        return validated_data

    def create_display_set(self, data):
        ds = DisplaySet.objects.create(reader_study=self.reader_study)
        ds.order = data.pop("order")
        ds.save()
        for slug in data:
            if not data[slug]:
                # Field is not filled in the form
                continue
            interface = ComponentInterface.objects.get(slug=slug)
            if interface.requires_file:
                user_upload = data[slug]
                transaction.on_commit(
                    add_file_to_display_set.signature(
                        kwargs={
                            "user_upload_pk": str(user_upload.pk),
                            "interface_pk": str(interface.pk),
                            "display_set_pk": str(ds.pk),
                        }
                    ).apply_async
                )
            elif interface.is_json_kind:
                civ = interface.create_instance(value=data[slug])
                ds.values.add(civ)
            elif interface.is_image_kind:
                if isinstance(data[slug], Image):
                    (
                        civ,
                        created,
                    ) = ComponentInterfaceValue.objects.get_or_create(
                        interface=interface, image=data[slug]
                    )
                    if created:
                        civ.full_clean()
                    ds.values.add(civ)
                else:
                    us = RawImageUploadSession.objects.create(
                        creator=self.request.user,
                    )
                    us.user_uploads.set(data[slug])
                    us.process_images(
                        linked_task=add_image_to_display_set.signature(
                            kwargs={
                                "display_set_pk": str(ds.pk),
                                "interface_pk": str(interface.pk),
                            },
                            immutable=True,
                        )
                    )

    def return_errors(self, errors):
        return JsonResponse(errors, status=400)

    def form_invalid(self, form):
        errors = form.errors
        try:
            self._process_new_interfaces()
        except ValidationError as e:
            errors.update(e.message_dict)
        return self.return_errors(errors)

    def form_valid(self, form):
        errors = {}
        try:
            data = self._process_new_interfaces()
        except ValidationError as e:
            errors.update(e.message_dict)

        try:
            data.update(form.cleaned_data)
            self.create_display_set(data)
        except ValidationError as e:
            errors.update(e.message_dict)

        if errors:
            return self.return_errors(errors)
        else:
            messages.success(
                self.request,
                "Display set created. Image and file import jobs have been queued.",
            )
            return JsonResponse({"redirect": self.get_success_url()})

    def get_success_url(self):
        return reverse(
            "reader-studies:display_sets", kwargs={"slug": self.kwargs["slug"]}
        )
