from dataclasses import dataclass
from functools import reduce
from operator import or_
from random import choice
from typing import Tuple

from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import (
    ImproperlyConfigured,
    NON_FIELD_ERRORS,
    ValidationError,
)
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms.utils import ErrorList
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.generic import ListView, TemplateView, UpdateView
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.challenges.models import Challenge
from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.subdomains.utils import reverse


@dataclass
class Highlight:
    title: str
    image: str
    url: str
    url_title: str
    description: str = ""
    bullet_points: list = list


class HomeTemplate(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        background_url = static(
            choice(
                [
                    "images/pathology_banner.jpg",
                    "images/ophthalmology_banner.png",
                    "images/radiology_banner_1.png",
                    "images/radiology_banner_2.png",
                ]
            )
        )

        highlights = [
            Highlight(
                title="Manage Your Data",
                bullet_points=[
                    "Upload medical imaging data easily and securely",
                    "Control who has access to the data",
                    "View data with our globally available browser-based workstations",
                ],
                url=reverse("archives:list"),
                url_title="Archives",
                image="images/archive.png",
            ),
            Highlight(
                title="Train Expert Annotators",
                bullet_points=[
                    "Create sets of questions that users must answer about a dataset",
                    "Invite clinical experts take part in the training",
                    "Deliver immediate feedback on performance",
                ],
                url=reverse("reader-studies:list"),
                url_title="Courses",
                image="images/education.png",
            ),
            Highlight(
                title="Gather Annotations",
                bullet_points=[
                    "Create your own set of questions for your dataset",
                    "Customise the hanging protocols and overlays",
                    "Use our intuitive workstations to view and report the images",
                ],
                url=reverse("reader-studies:list"),
                url_title="Reader Studies",
                image="images/annotation.png",
            ),
            Highlight(
                title="Benchmark Algorithms",
                bullet_points=[
                    "Manage your annotated training, test and validation data sets",
                    "Gather machine learning solutions for your clinical question",
                    "Objectively assess the performance of algorithms",
                ],
                url=reverse("challenges:list"),
                url_title="Challenges",
                image="images/challenge.png",
            ),
            Highlight(
                title="Deploy Your Algorithms",
                bullet_points=[
                    "Upload algorithm container images",
                    "Manage access for clinical and non-clinical researchers",
                    "Upload data for execution by your algorithm on our infrastructure",
                ],
                url=reverse("algorithms:list"),
                url_title="Algorithms",
                image="images/algorithms.png",
            ),
            Highlight(
                title="Find Certified Solutions",
                bullet_points=[
                    "Filter to easily find solutions to your clinical questions",
                    "Compare product specifications",
                    "Verify CE and FDA certification",
                ],
                url=reverse("products:product-list"),
                url_title="Products",
                image="images/products.png",
            ),
        ]

        context.update(
            {
                "all_users": get_user_model().objects.all(),
                "all_challenges": Challenge.objects.all(),
                "all_algorithms": Algorithm.objects.all(),
                "highlights": highlights,
                "jumbotron_background_url": background_url,
                "jumbotron_title": "Grand Challenge",
                "jumbotron_description": (
                    "A platform for end-to-end development of machine "
                    "learning solutions in biomedical imaging."
                ),
            }
        )
        return context


class PermissionRequestUpdate(
    UserIsNotAnonMixin,
    SuccessMessageMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    # The model that the permission request is for
    base_model = None
    # The namespace of the app to redirect to
    redirect_namespace = None
    # Checks on whether the permission request user is in these groups
    user_check_attrs = ["is_user", "is_editor"]
    raise_exception = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.base_model is None or self.redirect_namespace is None:
            raise ImproperlyConfigured(
                "`base_model` and `redirect_namespace` must be set."
            )

    @property
    def base_object(self):
        return get_object_or_404(self.base_model, slug=self.kwargs["slug"])

    def get_permission_object(self):
        return self.base_object

    def form_valid(self, form):
        permission_request = self.get_object()
        user = permission_request.user
        form.instance.user = user
        if not self.base_object.is_editor(self.request.user) and not any(
            getattr(self.base_object, f)(user) for f in self.user_check_attrs
        ):
            form.instance.status = self.model.PENDING
        try:
            redirect = super().form_valid(form)
            return redirect

        except ValidationError as e:
            form._errors[NON_FIELD_ERRORS] = ErrorList(e.messages)
            return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "permission_request": self.get_object(),
                "base_object": self.base_object,
            }
        )
        return context

    def get_success_message(self, cleaned_data):
        if not self.base_object.is_editor(self.request.user):
            return "You request for access has been sent to editors"
        return "Permission request successfully updated"

    def get_success_url(self):
        if not self.base_object.is_editor(self.request.user):
            return reverse(f"{self.redirect_namespace}:list")

        return reverse(
            f"{self.redirect_namespace}:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )


class PaginatedTableListView(ListView):
    columns = []

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update({"columns": self.columns})
        return context

    def get_paginator(self, *, data, page_size):
        return Paginator(data, page_size)

    def get_row_context(self, job, *args, **kwargs):
        pass

    def render_row_data(self, job, *args, **kwargs):
        return render_to_string(
            self.row_template,
            context=self.get_row_context(job, *args, **kwargs),
        ).split("<split/>")

    def get_data(self, jobs, *args, **kwargs):
        return [self.render_row_data(job, *args, **kwargs) for job in jobs]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            start = int(request.GET.get("start", 0))
            page_size = int(request.GET.get("length"))
            search = request.GET.get("search[value]")
            page = start // page_size + 1
            order_by = request.GET.get("order[0][column]")
            order_by = (
                self.columns[int(order_by)].sort_field
                if order_by
                else self.order_by
            )
            order_dir = request.GET.get("order[0][dir]", "desc")
            order_by = f"{'-' if order_dir == 'desc' else ''}{order_by}"
            qs = self.get_unfiltered_queryset()
            data = self.get_filtered_queryset(qs, search, order_by)
            paginator = self.get_paginator(data=data, page_size=page_size)
            jobs = paginator.page(page)
            return JsonResponse(
                {
                    "draw": int(request.GET.get("draw")),
                    "recordsTotal": qs.count(),
                    "recordsFiltered": paginator.count,
                    "data": self.get_data(jobs),
                }
            )
        return response

    def get_unfiltered_queryset(self):
        return self.object_list

    def get_filtered_queryset(self, queryset, search, order_by):
        if search:
            q = reduce(
                or_,
                [Q(**{f"{f}__icontains": search}) for f in self.search_fields],
                Q(),
            )
            queryset = queryset.filter(q)
        return queryset.order_by(order_by)


@dataclass
class Column:
    title: str
    sort_field: str
    classes: Tuple[str] = ()
