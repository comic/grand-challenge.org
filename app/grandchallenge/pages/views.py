from datetime import datetime

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import Http404
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from django_countries import countries
from guardian.mixins import LoginRequiredMixin

from grandchallenge.challenges.models import ChallengeRequest
from grandchallenge.charts.specs import stacked_bar, world_map
from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.evaluation.models import Submission
from grandchallenge.evaluation.utils import SubmissionKindChoices
from grandchallenge.pages.forms import PageCreateForm, PageUpdateForm
from grandchallenge.pages.models import Page
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class ChallengeFilteredQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(Q(challenge=self.request.challenge))


class ChallengeFormKwargsMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"challenge": self.request.challenge})
        return kwargs


class PageCreate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ChallengeFormKwargsMixin,
    CreateView,
):
    model = Page
    form_class = PageCreateForm
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def form_valid(self, form):
        form.instance.challenge = self.request.challenge
        return super().form_valid(form)


class PageList(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ChallengeFilteredQuerysetMixin,
    ListView,
):
    model = Page
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge


class PageDetail(
    UserPassesTestMixin, ChallengeFilteredQuerysetMixin, DetailView
):
    model = Page
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def test_func(self):
        user = self.request.user
        page = self.get_object()
        return page.can_be_viewed_by(user=user)


class ChallengeHome(PageDetail):
    def get_object(self, queryset=None):
        page = self.request.challenge.page_set.first()

        if page is None:
            raise Http404("No pages found for this challenge")

        return page


class PageUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ChallengeFilteredQuerysetMixin,
    ChallengeFormKwargsMixin,
    UpdateView,
):
    model = Page
    form_class = PageUpdateForm
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.move(form.cleaned_data["move"])
        return response


class PageDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ChallengeFilteredQuerysetMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = Page
    success_message = "Page was successfully deleted"
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_success_url(self):
        return reverse(
            "pages:list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )


class ChallengeStatistics(TemplateView):
    template_name = "pages/challenge_statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()

        participants = (
            self.request.challenge.get_participants().select_related(
                "user_profile", "verification"
            )
        )

        participants_countries = (
            participants.exclude(user_profile__country="")
            .values("user_profile__country")
            .annotate(country_count=Count("user_profile__country"))
            .order_by("-country_count")
            .values_list("user_profile__country", "country_count")
        )

        public_phases = self.request.challenge.phase_set.filter(public=True)

        submissions = (
            Submission.objects.filter(phase__in=public_phases)
            .values("phase__pk", "created__year", "created__month")
            .annotate(object_count=Count("phase__slug"))
            .order_by("created__year", "created__month", "phase__pk")
        )

        creators = (
            Submission.objects.filter(phase__in=public_phases)
            .values("phase__pk")
            .annotate(creators_count=Count("creator__pk", distinct=True))
            .order_by("phase__pk")
        )

        context.update(
            {
                "participants": world_map(
                    values=[
                        {
                            "id": countries.numeric(c[0], padded=True),
                            "participants": c[1],
                        }
                        for c in participants_countries
                    ]
                ),
                "participants_total": participants.count(),
                "submissions": stacked_bar(
                    values=[
                        {
                            "Month": datetime(
                                datum["created__year"],
                                datum["created__month"],
                                1,
                            ).isoformat(),
                            "New Submissions": datum["object_count"],
                            "Phase": datum["phase__pk"],
                        }
                        for datum in submissions
                    ],
                    lookup="New Submissions",
                    title="New Submissions per Month",
                    facet="Phase",
                    domain=[
                        (phase.pk, phase.title) for phase in public_phases
                    ],
                ),
                "algorithm_phases": self.request.challenge.phase_set.prefetch_related(
                    "submission_set"
                ).filter(
                    submission_kind=SubmissionKindChoices.ALGORITHM
                ),
                "statistics_for_phases": cache.get("statistics_for_phases"),
                "challenge_request": ChallengeRequest.objects.filter(
                    short_name=self.request.challenge.short_name,
                    status=ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
                ).first(),
                "creators": stacked_bar(
                    values=[
                        {
                            "Creators": datum["creators_count"],
                            "Phase": datum["phase__pk"],
                        }
                        for datum in creators
                    ],
                    lookup="Creators",
                    title="Creators per Phase",
                    facet="Phase",
                    domain=[
                        (phase.pk, phase.title) for phase in public_phases
                    ],
                ),
            }
        )

        return context
