from functools import cached_property

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import (
    AccessMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)
from guardian.mixins import LoginRequiredMixin
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.challenges.filters import ChallengeFilter
from grandchallenge.challenges.forms import (
    ChallengeRequestBudgetCalculatorForm,
    ChallengeRequestBudgetUpdateForm,
    ChallengeRequestForm,
    ChallengeRequestStatusUpdateForm,
    ChallengeRequestUpdateForm,
    ChallengeUpdateForm,
)
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    OnboardingTask,
)
from grandchallenge.challenges.serializers import PublicChallengeSerializer
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
)
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.mixins import ChallengeSubdomainObjectMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.verifications.views import VerificationRequiredMixin


class ActiveChallengeRequiredMixin(AccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.challenge.is_active:
            messages.error(
                request,
                "This action cannot be performed as the challenge is inactive. Please contact support.",
            )
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class ChallengeList(FilterMixin, ListView):
    model = Challenge
    ordering = ("-highlight", "-created")
    filter_class = ChallengeFilter
    paginate_by = 40
    queryset = Challenge.objects.filter(hidden=False).prefetch_related(
        "phase_set", "publications"
    )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context.update(
            {
                "jumbotron_title": "Challenges",
                "jumbotron_description": format_html(
                    (
                        "Here is an overview over the medical image analysis"
                        " challenges that have been hosted on Grand Challenge."
                        "<br>Please fill in <a href='{}'>this form</a> "
                        "if you would like to host your own challenge."
                    ),
                    reverse("challenges:requests-create"),
                ),
            }
        )
        return context


class UsersChallengeList(
    LoginRequiredMixin,
    ViewObjectPermissionListMixin,
    PaginatedTableListView,
):
    model = Challenge
    template_name = "challenges/challenge_users_list.html"
    row_template = "challenges/challenge_users_row.html"
    search_fields = ["title", "short_name", "description"]
    columns = [
        Column(title="Acronym", sort_field="short_name"),
        Column(title="Hidden", sort_field="hidden"),
        Column(
            title="Your Role(s)",
            sort_field=(
                "user_is_challenge_admin",
                "user_is_challenge_participant",
            ),
        ),
        Column(title="Status"),
        Column(title="Admins"),
        Column(title="Created", sort_field="created"),
        Column(title="Last Submission", sort_field="cached_latest_result"),
    ]
    default_sort_column = 1

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                # For displaying profile of admins
                "admins_group__user_set__user_profile",
                "admins_group__user_set__verification",
                # For displaying challenge status (badge)
                "phase_set",
            )
            .with_user_roles(user=self.request.user)
            .exclude(
                user_is_challenge_admin=False,
                user_is_challenge_participant=False,
            )
        )


class ChallengeUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    ChallengeSubdomainObjectMixin,
    UpdateView,
):
    model = Challenge
    slug_field = "short_name__iexact"
    slug_url_kwarg = "challenge_short_name"
    form_class = ChallengeUpdateForm
    success_message = "Challenge successfully updated"
    template_name_suffix = "_update"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        return reverse(
            "challenge-update",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )


class ChallengeRequestCreate(
    LoginRequiredMixin,
    VerificationRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = ChallengeRequest
    form_class = ChallengeRequestForm
    success_message = "A draft of your challenge request has been created!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"creator": self.request.user})
        return kwargs


class ChallengeRequestList(
    LoginRequiredMixin, ViewObjectPermissionListMixin, ListView
):
    model = ChallengeRequest
    raise_exception = True
    login_url = reverse_lazy("account_login")


class ChallengeRequestDetail(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    DetailView,
):
    model = ChallengeRequest
    permission_required = "view_challengerequest"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    @cached_property
    def detail_view_fields(self):
        result = [
            "title",
            "short_name",
            "contact_email",
            "abstract",
            "start_date",
            "end_date",
            "organizers",
            "challenge_setup",
            "challenge_fee_agreement",
        ]
        for field_name in (
            "affiliated_event",
            "data_set",
            "submission_assessment",
            "challenge_publication",
            "code_availability",
            "algorithm_inputs",
            "algorithm_outputs",
        ):
            if getattr(self.object, field_name):
                result.append(field_name)

        for field_name in (
            "task_types",
            "structures",
            "modalities",
        ):
            if getattr(self.object, field_name).exists():
                result.append(field_name)

        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        fields = {}
        label_overrides = {
            "challenge_setup": "Challenge technical setup",
            "short_name": "Acronym",
            "challenge_fee_agreement": "Pricing Policy Agreement",
        }
        for field_name in self.detail_view_fields:
            field = self.object._meta.get_field(field_name)
            label = label_overrides.get(field_name, field.verbose_name)
            if field.many_to_many:
                value = field.value_from_object(self.object)
                fields[label] = ", ".join(str(val) for val in value)
            else:
                fields[label] = field.value_to_string(self.object)

        context.update(
            {
                "fields": fields,
                # Information used by the budget table for the reviewers:
                "num_support_years": settings.CHALLENGE_NUM_SUPPORT_YEARS,
                "capacity_reservation_pack_size_in_euro": settings.CHALLENGE_CAPACITY_RESERVATION_PACK_SIZE_IN_EURO,
            }
        )
        return context


class ChallengeRequestUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = ChallengeRequest
    permission_required = "change_challengerequest"
    raise_exception = True
    form_class = ChallengeRequestUpdateForm
    login_url = reverse_lazy("account_login")
    template_name = "challenges/challengerequest_update_form.html"


class ChallengeRequestStatusUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = ChallengeRequest
    raise_exception = True
    form_class = ChallengeRequestStatusUpdateForm
    login_url = reverse_lazy("account_login")

    def form_valid(self, form):
        super().form_valid(form)
        # Handing of the state change is done in the model's save method,
        # so we need to only refresh the page to get the updated state

        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response

    def form_invalid(self, form):
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    messages.error(self.request, error)
                else:
                    messages.error(
                        self.request, f"{form.fields[field].label}: {error}"
                    )

        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response


class ChallengeRequestProcess(ChallengeRequestStatusUpdate):
    permission_required = "review_challengerequest"


class ChallengeRequestSubmit(ChallengeRequestStatusUpdate):
    permission_required = "change_challengerequest"


class ChallengeRequestBudgetUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = ChallengeRequest
    form_class = ChallengeRequestBudgetUpdateForm
    permission_required = "review_challengerequest"
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "challenges/challengerequest_budget_form.html"

    def form_valid(self, form):
        super().form_valid(form)
        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response


class ChallengeRequestBudgetCalculator(
    LoginRequiredMixin,
    UserPassesTestMixin,
    FormView,
):
    form_class = ChallengeRequestBudgetCalculatorForm
    login_url = reverse_lazy("account_login")
    template_name = "challenges/challengerequest_budget_calculator.html"

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        raise Http404()

    def get_initial(self):
        return {
            "algorithm_selectable_gpu_type_choices_for_tasks": [
                ["", "T4"],
                ["", "T4", "A10G"],
            ],
            "algorithm_maximum_settable_memory_gb_for_tasks": [32, 32],
            "average_size_test_case_mb_for_tasks": [10, 40],
            "inference_time_average_minutes_for_tasks": [5, 10],
            "task_ids": [1, 2],
            "task_id_for_phases": [1, 1, 2, 2],
            "number_of_teams_for_phases": [10, 10, 20, 20],
            "number_of_submissions_per_team_for_phases": [10, 1, 10, 1],
            "number_of_test_cases_for_phases": [3, 300, 3, 300],
        }

    def form_valid(self, form):
        challenge_request = ChallengeRequest(
            **form.cleaned_data
        )  # unsaved instance
        return render(
            self.request,
            "challenges/partials/budget_table.html",
            {
                "object": challenge_request,
                "num_support_years": settings.CHALLENGE_NUM_SUPPORT_YEARS,
                "capacity_reservation_pack_size_in_euro": settings.CHALLENGE_CAPACITY_RESERVATION_PACK_SIZE_IN_EURO,
            },
        )

    def form_invalid(self, form):
        return HttpResponse(str(form.errors))


class ChallengeCostOverview(
    LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    template_name = "challenges/challenge_costs_overview.html"
    permission_required = "challenges.view_challengerequest"
    model = Challenge

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .with_available_compute()
            .with_invoices_with_budget_authorization()
            .prefetch_related("phase_set")
        )


class ChallengeViewSet(ReadOnlyModelViewSet):
    queryset = Challenge.objects.all().prefetch_related(
        "phase_set",
        "incentives",
        # Put the most cited publications first
        Prefetch(
            "publications",
            queryset=Publication.objects.order_by(
                F("referenced_by_count").desc(nulls_last=True)
            ),
        ),
    )
    serializer_class = PublicChallengeSerializer
    permission_classes = [DjangoObjectPermissions]
    filter_backends = [ViewObjectPermissionsFilter]
    # We do not want to serialize the pk so lookup by short_name, but call it slug
    lookup_field = "short_name"
    lookup_url_kwarg = "slug"


class OnboardingTaskList(
    LoginRequiredMixin,
    ViewObjectPermissionListMixin,
    ListView,
):
    model = OnboardingTask
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["all_tasks_are_complete"] = all(
            object.complete for object in context["object_list"]
        )

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            challenge=self.request.challenge
        ).with_overdue_status()

        # Pe-ordering the queryset ensures nothing jumps around when the datatable initializes
        queryset = queryset.order_by("complete", "deadline")

        return queryset


class OnboardingTaskComplete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = OnboardingTask
    fields = ("complete",)
    permission_required = "change_onboardingtask"
    raise_exception = True
    login_url = reverse_lazy("account_login")
    http_method_names = ["post"]

    def get_success_url(self):
        return reverse(
            "challenge-onboarding-task-list",
            kwargs={
                "challenge_short_name": self.object.challenge.short_name,
            },
        )

    def get_success_message(self, cleaned_data):
        msg = f"Succesfully marked {self.object.title!r} "

        if cleaned_data["complete"]:
            msg += "as complete"
        else:
            msg += "as incomplete"

        return msg
