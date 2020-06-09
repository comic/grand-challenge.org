from functools import reduce
from operator import or_

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
from django.views.generic import ListView, TemplateView, UpdateView
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.core.permissions.mixins import UserIsNotAnonMixin
from grandchallenge.subdomains.utils import reverse


class HomeTemplate(TemplateView):
    template_name = "home.html"


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
    def get_paginator(self, *, data, page_size):
        return Paginator(data, page_size)

    def get_row_context(self, result, *args, **kwargs):
        pass

    def render_row_data(self, result, *args, **kwargs):
        return render_to_string(
            self.row_template, context=self.get_row_context(result)
        ).split("<split/>")

    def get_data(self, results, *args, **kwargs):
        return [self.render_row_data(result) for result in results]

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.is_ajax():
            start = int(request.GET.get("start", 0))
            page_size = int(request.GET.get("length"))
            search = request.GET.get("search[value]")
            page = start // page_size + 1
            order_by = request.GET.get("order[0][column]")
            order_by = (
                self.columns[int(order_by)] if order_by else self.order_by
            )
            order_dir = request.GET.get("order[0][dir]", "desc")
            order_by = f"{'-' if order_dir == 'desc' else ''}{order_by}"
            qs = self.get_unfiltered_queryset()
            data = self.get_filtered_queryset(qs, search, order_by)
            paginator = self.get_paginator(data=data, page_size=page_size)
            results = paginator.page(page)
            return JsonResponse(
                {
                    "draw": int(request.GET.get("draw")),
                    "recordsTotal": qs.count(),
                    "recordsFiltered": paginator.count,
                    "data": self.get_data(results),
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
