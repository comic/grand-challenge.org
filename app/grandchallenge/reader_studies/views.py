import csv
import re

from dal import autocomplete
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    PermissionDenied,
    ValidationError,
)
from django.core.paginator import Paginator
from django.db import transaction
from django.forms.utils import ErrorList
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import format_html
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
from rest_framework.decorators import action
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.viewsets import (
    ModelViewSet,
    ReadOnlyModelViewSet,
)
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.cases.forms import UploadRawImagesForm
from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin
from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.core.permissions.rest_framework import (
    DjangoObjectOnlyPermissions,
    DjangoObjectOnlyWithCustomPostPermissions,
)
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.core.views import PermissionRequestUpdate
from grandchallenge.reader_studies.filters import ReaderStudyFilter
from grandchallenge.reader_studies.forms import (
    AnswersRemoveForm,
    CategoricalOptionFormSet,
    EditorsForm,
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


class ReaderStudyList(PermissionListMixin, FilterMixin, ListView):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.view_{ReaderStudy._meta.model_name}"
    )
    ordering = "-created"
    filter_class = ReaderStudyFilter

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
            readers = [
                {
                    "obj": reader,
                    "progress": self.object.get_progress_for_user(reader),
                }
                for reader in self.object.readers_group.user_set.all()
            ]

            reader_remove_form = ReadersForm()
            reader_remove_form.fields["action"].initial = ReadersForm.REMOVE
            editor_remove_form = EditorsForm()
            editor_remove_form.fields["action"].initial = EditorsForm.REMOVE
            answers_remove_form = AnswersRemoveForm()

            pending_permission_requests = ReaderStudyPermissionRequest.objects.filter(
                reader_study=context["object"],
                status=ReaderStudyPermissionRequest.PENDING,
            ).count()

            context.update(
                {
                    "readers": readers,
                    "editor_remove_form": editor_remove_form,
                    "reader_remove_form": reader_remove_form,
                    "answers_remove_form": answers_remove_form,
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


class ReaderStudyUpdate(
    UserFormKwargsMixin,
    LoginRequiredMixin,
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


class ReaderStudyImages(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = ReaderStudy
    permission_required = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )
    raise_exception = True
    template_name = "reader_studies/readerstudy_images.html"

    def get_context_data(self, **kwarsg):
        context = super().get_context_data(**kwarsg)
        paginator = Paginator(self.object.images.all(), 15)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        context.update({"page_obj": page_obj})
        return context


class QuestionOptionMixin(object):
    def validate_options(self, form, _super):
        context = self.get_context_data()
        options = context["options"]
        if form.data["answer_type"] not in [
            Question.ANSWER_TYPE_CHOICE,
            Question.ANSWER_TYPE_MULTIPLE_CHOICE,
            Question.ANSWER_TYPE_MULTIPLE_CHOICE_DROPDOWN,
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
    QuestionOptionMixin,
    LoginRequiredMixin,
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

    def get_success_url(self):
        return self.object.reader_study.get_absolute_url()


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

    def get_success_url(self):
        return self.object.reader_study.get_absolute_url()


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

    def get_success_url(self):
        return self.object.get_absolute_url()


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


class ReaderStudyUserAutocomplete(
    LoginRequiredMixin, UserPassesTestMixin, autocomplete.Select2QuerySetView
):
    def test_func(self):
        group_pks = (
            ReaderStudy.objects.all()
            .select_related("editors_group")
            .values_list("editors_group__pk", flat=True)
        )
        return (
            self.request.user.is_superuser
            or self.request.user.groups.filter(pk__in=group_pks).exists()
        )

    def get_queryset(self):
        qs = (
            get_user_model()
            .objects.all()
            .order_by("username")
            .exclude(username=settings.ANONYMOUS_USER_NAME)
        )

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
    raise_exception = True

    def get_permission_object(self):
        return self.reader_study

    @property
    def reader_study(self):
        return get_object_or_404(ReaderStudy, slug=self.kwargs["slug"])

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
    UserIsNotAnonMixin, SuccessMessageMixin, CreateView
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


class ExportCSVMixin(object):
    def _create_dicts(self, headers, data):
        return map(lambda x: dict(zip(headers, x)), data)

    def _preprocess_data(self, data):
        processed = []
        for entry in data:
            processed.append(
                map(lambda x: re.sub(r"[\n\r\t]", " ", str(x)), entry)
            )
        return processed

    def _create_csv_response(self, data, headers, filename="export.csv"):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.DictWriter(
            response,
            quoting=csv.QUOTE_ALL,
            escapechar="\\",
            fieldnames=headers,
        )
        writer.writeheader()
        csv_dict = self._create_dicts(headers, self._preprocess_data(data))
        writer.writerows(csv_dict)

        return response


class ReaderStudyViewSet(ExportCSVMixin, ReadOnlyModelViewSet):
    serializer_class = ReaderStudySerializer
    queryset = ReaderStudy.objects.all().prefetch_related(
        "images", "questions__options"
    )
    permission_classes = [DjangoObjectOnlyPermissions]
    filter_backends = [ObjectPermissionsFilter]
    change_permission = (
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}"
    )

    def _check_change_perms(self, user, obj):
        if not (user and user.has_perm(self.change_permission, obj)):
            raise Http404()

    @action(detail=True)
    def export_answers(self, request, pk=None):
        reader_study = self.get_object()
        self._check_change_perms(request.user, reader_study)
        data = []
        headers = []
        for answer in (
            Answer.objects.select_related("question__reader_study")
            .select_related("creator")
            .prefetch_related("images")
            .filter(question__reader_study=reader_study, is_ground_truth=False)
        ):
            data += [answer.csv_values]
            if len(answer.csv_headers) > len(headers):
                headers = answer.csv_headers
        return self._create_csv_response(
            data,
            headers,
            filename=f"{reader_study.slug}-answers-{timezone.now().isoformat()}.csv",
        )

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
    filter_backends = [ObjectPermissionsFilter]


class AnswerViewSet(ModelViewSet):
    serializer_class = AnswerSerializer
    queryset = (
        Answer.objects.all()
        .select_related("creator", "question__reader_study")
        .prefetch_related("images")
    )
    permission_classes = [DjangoObjectOnlyWithCustomPostPermissions]
    filter_backends = [DjangoFilterBackend, ObjectPermissionsFilter]
    filterset_fields = ["question__reader_study"]

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
