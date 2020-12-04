from dataclasses import dataclass
from functools import reduce
from operator import or_
from typing import Tuple

from django.core.paginator import Paginator
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

    def get_paginator(self, *, data, page_size):
        return Paginator(data, page_size)

    def get_row_context(self, obj, *args, **kwargs):
        return {"object": obj}

    def render_row_data(self, obj, *args, **kwargs):
        return render_to_string(
            self.row_template,
            context=self.get_row_context(obj, *args, **kwargs),
        ).split("<split/>")

    def get_data(self, objects, *args, **kwargs):
        return [self.render_row_data(o, *args, **kwargs) for o in objects]

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
            objects = paginator.page(page)
            return JsonResponse(
                {
                    "draw": int(request.GET.get("draw")),
                    "recordsTotal": qs.count(),
                    "recordsFiltered": paginator.count,
                    "data": self.get_data(objects),
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
    classes: Tuple[str, ...] = ()
    identifier: str = ""
