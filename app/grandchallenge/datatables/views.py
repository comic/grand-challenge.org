from dataclasses import dataclass
from functools import reduce
from operator import or_

from django.core.paginator import EmptyPage
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import ListView


class PaginatedTableListView(ListView):
    columns = []
    search_fields = []
    default_sort_column = 0
    text_align = "center"
    default_sort_order = "desc"

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update(
            {
                "columns": self.columns,
                "default_sort_column": self.default_sort_column,
                "text_align": self.text_align,
                "default_sort_order": self.default_sort_order,
            }
        )
        return context

    def render_row(self, *, object_, page_context, request):
        return render_to_string(
            self.row_template,
            context={**page_context, "object": object_},
            request=request,
        ).split("<split></split>")

    def render_rows(self, *, object_list, request):
        page_context = self.get_context_data(object_list=object_list)
        return [
            self.render_row(
                object_=o, page_context=page_context, request=request
            )
            for o in object_list
        ]

    def get_order_by(self, *, column_index, direction):
        try:
            order_by = self.columns[int(column_index)].sort_field
        except IndexError:
            return None

        prefix = "-" if direction == "desc" else ""

        return f"{prefix}{order_by}"

    def draw_response(self, *, request):
        start = int(request.POST.get("start", 0))
        page_size = int(request.POST.get("length"))
        search = request.POST.get("search[value]")
        draw = int(request.POST.get("draw"))
        column_index = (
            request.POST.get("order[0][column]") or self.default_sort_column
        )
        direction = (
            request.POST.get("order[0][dir]") or self.default_sort_order
        )

        page = start // page_size + 1
        order_by = self.get_order_by(
            column_index=column_index, direction=direction
        )
        data = self.filter_queryset(self.object_list, search, order_by)
        paginator = self.get_paginator(queryset=data, per_page=page_size)

        try:
            objects = paginator.page(page)
        except EmptyPage:
            # If the page is out of range, show the last page
            objects = paginator.page(paginator.num_pages)

        return JsonResponse(
            {
                "draw": draw,
                "recordsTotal": self.object_list.count(),
                "recordsFiltered": paginator.count,
                "data": self.render_rows(object_list=objects, request=request),
            }
        )

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return self.draw_response(request=request)
        else:
            return response

    def post(self, request, *args, **kwargs):
        """Handles giant URL queries from jquery datatables"""
        return self.get(request, *args, **kwargs)

    def filter_queryset(self, queryset, search, order_by):
        if search:
            q = reduce(
                or_,
                [Q(**{f"{f}__icontains": search}) for f in self.search_fields],
                Q(),
            )
            queryset = queryset.filter(q)
        if order_by:
            queryset = queryset.order_by(order_by)
        return queryset.distinct()


@dataclass
class Column:
    title: str
    sort_field: str = ""
    classes: tuple[str, ...] = ()
    identifier: str = ""

    def __post_init__(self):
        if not self.sort_field:
            self.classes = (*self.classes, "nonSortable")
