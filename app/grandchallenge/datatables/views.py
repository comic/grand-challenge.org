from dataclasses import dataclass
from functools import reduce
from operator import or_
from typing import Callable, Optional, Tuple

from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import ListView


class PaginatedTableListView(ListView):
    columns = []
    search_fields = []
    default_sort_column = 0

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update(
            {
                "columns": self.columns,
                "default_sort_column": self.default_sort_column,
            }
        )
        return context

    def render_row(self, *, object_, page_context):
        return render_to_string(
            self.row_template, context={**page_context, "object": object_},
        ).split("<split></split>")

    def render_rows(self, *, object_list):
        page_context = self.get_context_data(object_list=object_list)
        return [
            self.render_row(object_=o, page_context=page_context)
            for o in object_list
        ]

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
            data = self.filter_queryset(self.object_list, search, order_by)
            paginator = self.get_paginator(queryset=data, per_page=page_size)
            objects = paginator.page(page)

            show_columns = []
            for c in self.columns:
                show_columns.append(
                    c.optional_condition is None
                    or any(c.optional_condition(o) for o in objects)
                )
            return JsonResponse(
                {
                    "draw": int(request.GET.get("draw")),
                    "recordsTotal": self.object_list.count(),
                    "recordsFiltered": paginator.count,
                    "data": self.render_rows(object_list=objects),
                    "showColumns": show_columns,
                }
            )
        return response

    def filter_queryset(self, queryset, search, order_by):
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
    classes: Tuple[str, ...] = ()
    identifier: str = ""

    # A column will be hidden when the `optional_condition` evaluates to False
    # for every object shown in the current list (page). `optional_condition`
    # is a function that consumes the current object as argument
    optional_condition: Optional[Callable] = None
