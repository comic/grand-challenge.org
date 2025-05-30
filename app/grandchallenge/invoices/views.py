from django.views.generic import ListView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
)
from grandchallenge.invoices.models import Invoice
from grandchallenge.subdomains.utils import reverse_lazy


class InvoiceList(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ListView,
):
    model = Invoice
    permission_required = "change_challenge"
    ordering = "created"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(context["object_list"].status_aggregates)
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            challenge=self.request.challenge
        ).with_overdue_status()
