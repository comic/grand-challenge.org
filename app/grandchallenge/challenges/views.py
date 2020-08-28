from functools import reduce
from operator import or_

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from grandchallenge.challenges.forms import (
    ChallengeCreateForm,
    ChallengeUpdateForm,
    ExternalChallengeUpdateForm,
)
from grandchallenge.challenges.models import (
    BodyRegion,
    Challenge,
    ChallengeSeries,
    ExternalChallenge,
    ImagingModality,
    TaskType,
)
from grandchallenge.core.permissions.mixins import (
    UserIsChallengeAdminMixin,
    UserIsNotAnonMixin,
    UserIsStaffMixin,
)
from grandchallenge.core.templatetags.random_encode import random_encode
from grandchallenge.subdomains.mixins import ChallengeSubdomainObjectMixin
from grandchallenge.subdomains.utils import reverse


class ChallengeCreate(UserIsNotAnonMixin, SuccessMessageMixin, CreateView):
    model = Challenge
    form_class = ChallengeCreateForm
    success_message = "Challenge successfully created"

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)


class ChallengeList(TemplateView):
    paginate_by = 40
    template_name = "challenges/challenge_list.html"

    @property
    def _search_filter(self):
        search_query = self._current_search

        q = Q()

        if search_query:
            search_fields = [
                "title",
                "short_name",
                "description",
                "event_name",
            ]
            q = reduce(
                or_,
                [
                    Q(**{f"{f}__icontains": search_query})
                    for f in search_fields
                ],
                Q(),
            )

        return q

    @property
    def _current_page(self):
        return int(self.request.GET.get("page", 1))

    @property
    def _current_search(self):
        return self.request.GET.get("search", "")

    def _get_page(self):
        int_paginator = Paginator(
            Challenge.objects.filter(hidden=False)
            .filter(self._search_filter)
            .prefetch_related("phase_set")
            .order_by("-created"),
            self.paginate_by // 2,
        )
        ext_paginator = Paginator(
            ExternalChallenge.objects.filter(hidden=False)
            .filter(self._search_filter)
            .order_by("-created"),
            self.paginate_by // 2,
        )

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

        return [*int_page, *ext_page], num_pages, num_results

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)

        modalities = ImagingModality.objects.all()
        task_types = TaskType.objects.all()
        regions = BodyRegion.objects.all().prefetch_related(
            "bodystructure_set"
        )
        challenge_series = ChallengeSeries.objects.all()

        page_obj, num_pages, num_results = self._get_page()

        context.update(
            {
                "modalities": modalities,
                "body_regions": regions,
                "task_types": task_types,
                "challenge_series": challenge_series,
                "page_obj": page_obj,
                "num_pages": num_pages,
                "num_results": num_results,
                "current_page": self._current_page,
                "current_search": self._current_search,
                "jumbotron_title": "Challenges",
                "jumbotron_description": format_html(
                    (
                        "Here is an overview of all challenges that have been "
                        "organised within the area of medical image analysis "
                        "that we are aware of. Please <a href='{}'>contact "
                        "us</a> if you want to advertise your challenge or "
                        "know of any study that would fit in this overview."
                    ),
                    random_encode("mailto:support@grand-challenge.org"),
                ),
            }
        )

        return context


class UsersChallengeList(UserIsNotAnonMixin, ListView):
    model = Challenge
    template_name = "challenges/challenge_users_list.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(participants_group__in=self.request.user.groups.all())
                | Q(admins_group__in=self.request.user.groups.all())
            )
        return queryset


class ChallengeUpdate(
    UserIsChallengeAdminMixin,
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


class ExternalChallengeCreate(
    UserIsStaffMixin, SuccessMessageMixin, CreateView
):
    model = ExternalChallenge
    form_class = ExternalChallengeUpdateForm
    success_message = (
        "Your challenge has been successfully submitted. "
        "An admin will review your challenge before it is published."
    )

    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("challenges:list")


class ExternalChallengeUpdate(
    UserIsStaffMixin, SuccessMessageMixin, UpdateView
):
    model = ExternalChallenge
    slug_field = "short_name__iexact"
    slug_url_kwarg = "short_name"
    form_class = ExternalChallengeUpdateForm
    template_name_suffix = "_update"
    success_message = "Challenge updated"

    def get_success_url(self):
        return reverse("challenges:list")


class ExternalChallengeList(UserIsStaffMixin, ListView):
    model = ExternalChallenge


class ExternalChallengeDelete(UserIsStaffMixin, DeleteView):
    model = ExternalChallenge
    slug_field = "short_name__iexact"
    slug_url_kwarg = "short_name"
    success_message = "External challenge was successfully deleted"

    def get_success_url(self):
        return reverse("challenges:external-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)
