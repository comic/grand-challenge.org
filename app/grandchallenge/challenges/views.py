from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Prefetch, Q
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from guardian.mixins import LoginRequiredMixin
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.challenges.emails import send_challenge_status_update_email
from grandchallenge.challenges.filters import ChallengeFilter
from grandchallenge.challenges.forms import (
    ChallengeRequestBudgetUpdateForm,
    ChallengeRequestForm,
    ChallengeRequestStatusUpdateForm,
    ChallengeUpdateForm,
)
from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.challenges.serializers import PublicChallengeSerializer
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.mixins import ChallengeSubdomainObjectMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.verifications.views import VerificationRequiredMixin


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


class UsersChallengeList(LoginRequiredMixin, PaginatedTableListView):
    model = Challenge
    template_name = "challenges/challenge_users_list.html"
    row_template = "challenges/challenge_users_row.html"
    search_fields = ["title", "short_name", "description"]
    columns = [
        Column(title="Name", sort_field="short_name"),
        Column(title="Created", sort_field="created"),
        Column(title="Admins", sort_field="created"),
        Column(title="Description", sort_field="description"),
    ]
    default_sort_column = 1

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .prefetch_related(
                "admins_group__user_set__user_profile",
                "admins_group__user_set__verification",
            )
        )
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(participants_group__in=self.request.user.groups.all())
                | Q(admins_group__in=self.request.user.groups.all())
            )
        return queryset


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
    success_message = "Your request has been sent to the reviewers."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"creator": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse("challenges:requests-list")


class ChallengeRequestList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = ChallengeRequest
    permission_required = "view_challengerequest"
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
    detail_view_fields = (
        "title",
        "short_name",
        "start_date",
        "end_date",
        "organizers",
        "abstract",
        "affiliated_event",
        "task_types",
        "modalities",
        "structures",
        "challenge_setup",
        "data_set",
        "submission_assessment",
        "challenge_publication",
        "code_availability",
        "algorithm_inputs",
        "algorithm_outputs",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        fields = {
            field.verbose_name: field.value_to_string(self.object)
            for field in self.object._meta.fields
            if field.name in self.detail_view_fields
        }
        context.update(
            {
                "fields": fields,
            }
        )
        return context


class ChallengeRequestStatusUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = ChallengeRequest
    form_class = ChallengeRequestStatusUpdateForm
    permission_required = "change_challengerequest"
    template_name = "challenges/challengerequest_status_form.html"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def form_valid(self, form):
        super().form_valid(form)
        if (
            form.instance._orig_status
            == form.instance.ChallengeRequestStatusChoices.PENDING
            and form.instance._orig_status != form.instance.status
        ):
            if (
                form.instance.status
                == form.instance.ChallengeRequestStatusChoices.ACCEPTED
            ):
                challenge = form.instance.create_challenge()
            else:
                challenge = None
            send_challenge_status_update_email(
                challengerequest=form.instance, challenge=challenge
            )

        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response


class ChallengeRequestBudgetUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = ChallengeRequest
    form_class = ChallengeRequestBudgetUpdateForm
    permission_required = "change_challengerequest"
    raise_exception = True
    login_url = reverse_lazy("account_login")
    template_name = "challenges/challengerequest_budget_form.html"

    def form_valid(self, form):
        super().form_valid(form)
        response = HttpResponse()
        response["HX-Refresh"] = "true"
        return response


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
            .with_most_recent_submission_datetime()
            .prefetch_related("phase_set")
            .order_by(
                F("most_recent_submission_datetime").desc(nulls_last=True)
            )
        )


class ChallengeCostCalculation(
    LoginRequiredMixin, VerificationRequiredMixin, TemplateView
):
    template_name = "challenges/challenge_cost.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        try:
            number_of_tasks = int(request.GET.get("number_of_tasks"))
            average_size_of_test_image_in_mb = int(
                request.GET.get("average_size_of_test_image_in_mb")
            )
            inference_time_limit_in_minutes = int(
                request.GET.get("inference_time_limit_in_minutes")
            )
            phase_1_number_of_test_images = int(
                request.GET.get("phase_1_number_of_test_images")
            )
            phase_2_number_of_test_images = int(
                request.GET.get("phase_2_number_of_test_images")
            )
            phase_1_number_of_submissions_per_team = int(
                request.GET.get("phase_1_number_of_submissions_per_team")
            )
            phase_2_number_of_submissions_per_team = int(
                request.GET.get("phase_2_number_of_submissions_per_team")
            )
            expected_number_of_teams = int(
                request.GET.get("expected_number_of_teams")
            )
            challenge_request = ChallengeRequest(
                number_of_tasks=number_of_tasks,
                average_size_of_test_image_in_mb=average_size_of_test_image_in_mb,
                expected_number_of_teams=expected_number_of_teams,
                inference_time_limit_in_minutes=inference_time_limit_in_minutes,
                phase_1_number_of_test_images=phase_1_number_of_test_images,
                phase_2_number_of_test_images=phase_2_number_of_test_images,
                phase_1_number_of_submissions_per_team=phase_1_number_of_submissions_per_team,
                phase_2_number_of_submissions_per_team=phase_2_number_of_submissions_per_team,
            )

            context.update(
                {
                    "object": challenge_request,
                    "num_support_years": settings.CHALLENGE_NUM_SUPPORT_YEARS,
                }
            )

            if (
                phase_1_number_of_test_images > 1000
                or phase_2_number_of_test_images > 1000
            ):
                context["image_warning"] = format_html(
                    (
                        "You specified more than 1000 test images in one or both of your phases. "
                        "Be reminded that Grand Challenge starts a separate algorithm job per image. "
                        "When the images are small, it is better to <a href='{}'>bundle them into sets of images</a>."
                    ),
                    "https://grand-challenge.org/documentation/create-your-own-challenge/#budget-batched-images",
                )

            if inference_time_limit_in_minutes < 5:
                context["runtime_warning"] = (
                    "You specified an average algorithm job run time of less than 5 minutes. "
                    "This is unrealistic since this time includes i/o operations, "
                    "model loading and preprocessing next to the actual algorithm run time. "
                    "In our experience, a reasonable lower limit is 5 minutes."
                )

            if average_size_of_test_image_in_mb > 10000:
                context["image_size_warning"] = (
                    "The maximum image size is 10GB."
                )
        except (ValueError, TypeError):
            context["error"] = (
                "You need to fill in all the fields in the cost estimate box to calculate the costs."
            )

        return TemplateResponse(
            request=request,
            template=self.template_name,
            context=context,
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
    filter_backends = [ObjectPermissionsFilter]
    # We do not want to serialize the pk so lookup by short_name, but call it slug
    lookup_field = "short_name"
    lookup_url_kwarg = "slug"
