from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from guardian.mixins import LoginRequiredMixin
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.challenges.emails import send_challenge_status_update_email
from grandchallenge.challenges.filters import (
    ChallengeFilter,
    InternalChallengeFilter,
)
from grandchallenge.challenges.forms import (
    ChallengeRequestForm,
    ChallengeRequestUpdateForm,
    ChallengeUpdateForm,
    ExternalChallengeUpdateForm,
)
from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    ExternalChallenge,
)
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.datatables.views import Column, PaginatedTableListView
from grandchallenge.subdomains.mixins import ChallengeSubdomainObjectMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy
from grandchallenge.verifications.views import VerificationRequiredMixin


class ChallengeList(FilterMixin, ListView):
    model = Challenge
    ordering = ("-highlight", "-created")
    filter_class = InternalChallengeFilter
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


class CombinedChallengeList(TemplateView):
    paginate_by = 40
    template_name = "challenges/combined_challenge_list.html"

    @property
    def _current_page(self):
        return int(self.request.GET.get("page", 1))

    @property
    def _filters_applied(self):
        return any(k for k in self.request.GET if k.lower() != "page")

    def _get_page(self):
        int_qs = (
            Challenge.objects.filter(hidden=False)
            .prefetch_related("phase_set", "publications")
            .order_by("-highlight", "-created")
        )
        self.int_filter = ChallengeFilter(self.request.GET, int_qs)
        ext_qs = (
            ExternalChallenge.objects.filter(hidden=False)
            .prefetch_related("publications")
            .order_by("-created")
        )
        self.ext_filter = ChallengeFilter(self.request.GET, ext_qs)

        total_count = int_qs.count() + ext_qs.count()

        int_paginator = Paginator(self.int_filter.qs, self.paginate_by // 2)
        ext_paginator = Paginator(self.ext_filter.qs, self.paginate_by // 2)

        num_pages = max(int_paginator.num_pages, ext_paginator.num_pages)
        num_results = int_paginator.count + ext_paginator.count

        try:
            int_page = int_paginator.page(self._current_page)
        except EmptyPage:
            int_page = []

        try:
            ext_page = ext_paginator.page(self._current_page)
        except EmptyPage:
            ext_page = []

        return [*int_page, *ext_page], num_pages, num_results, total_count

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)

        page_obj, num_pages, num_results, total_count = self._get_page()

        context.update(
            {
                "filter": self.int_filter,
                "filters_applied": self._filters_applied,
                "page_obj": page_obj,
                "num_pages": num_pages,
                "num_results": num_results,
                "total_count": total_count,
                "current_page": self._current_page,
                "next_page": self._current_page + 1,
                "previous_page": self._current_page - 1,
                "jumbotron_title": "Challenges",
                "jumbotron_description": format_html(
                    (
                        "Here is an overview of all challenges that have been "
                        "organised within the area of medical image analysis "
                        "that we are aware of. Please <a href='{}'>contact "
                        "us</a> if you want to advertise your challenge or "
                        "know of any study that would fit in this overview."
                    ),
                    mark_safe(
                        random_encode("mailto:support@grand-challenge.org")
                    ),
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
            "update",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )


class ExternalChallengeCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = ExternalChallenge
    form_class = ExternalChallengeUpdateForm
    success_message = (
        "Your challenge has been successfully submitted. "
        "An admin will review your challenge before it is published."
    )
    raise_exception = True
    permission_required = "challenges.add_externalchallenge"

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("challenges:list")


class ExternalChallengeUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    UpdateView,
):
    model = ExternalChallenge
    slug_field = "short_name__iexact"
    slug_url_kwarg = "short_name"
    form_class = ExternalChallengeUpdateForm
    template_name_suffix = "_update"
    success_message = "Challenge updated"
    raise_exception = True
    permission_required = "challenges.change_externalchallenge"

    def get_success_url(self):
        return reverse("challenges:list")


class ExternalChallengeList(
    LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    model = ExternalChallenge
    raise_exception = True
    permission_required = "challenges.view_externalchallenge"


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
        return reverse("challenges:list")


class ChallengeRequestList(
    LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    model = ChallengeRequest
    permission_required = "challenges.view_challengerequest"
    paginate_by = 50
    ordering = ["-created"]


class ChallengeRequestDetail(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    model = ChallengeRequest
    permission_required = "challenges.view_challengerequest"
    detail_view_fields = (
        "title",
        "short_name",
        "challenge_type",
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
    budget_fields = (
        "expected_number_of_teams",
        "number_of_tasks",
        "inference_time_limit_in_minutes",
        "average_size_of_test_image_in_mb",
        "phase_1_number_of_submissions_per_team",
        "phase_1_number_of_test_images",
        "phase_2_number_of_submissions_per_team",
        "phase_2_number_of_test_images",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        fields = {
            field.verbose_name: field.value_to_string(self.object)
            for field in self.object._meta.fields
            if field.name in self.detail_view_fields
        }
        budget_fields = {
            field.verbose_name: field.value_to_string(self.object)
            for field in self.object._meta.fields
            if field.name in self.budget_fields
        }
        context.update(
            {
                "fields": fields,
                "budget": self.object.budget,
                "budget_fields": budget_fields,
            }
        )
        return context


class ChallengeRequestUpdate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = ChallengeRequest
    form_class = ChallengeRequestUpdateForm
    permission_required = "challenges.change_challengerequest"

    def form_valid(self, form):
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
        return super().form_valid(form)
