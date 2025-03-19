from django.views.generic import ListView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.invoices.models import Invoice
from grandchallenge.subdomains.utils import reverse_lazy


class InvoiceList(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
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

        context["num_is_due"] = sum(
            obj.is_due for obj in context["object_list"]
        )
        context["num_is_overdue"] = sum(
            obj.is_overdue for obj in context["object_list"]
        )

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(challenge=self.request.challenge)
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)
        return queryset
