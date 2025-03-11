from django.views.generic import DetailView, ListView
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
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context["outstanding_invoices"] = any(
            (
                obj.payment_type != obj.PaymentTypeChoices.COMPLIMENTARY
                and obj.payment_status == obj.PaymentStatusChoices.ISSUED
            )
            for obj in context["object_list"]
        )

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(challenge=self.request.challenge)
        return queryset


class InvoiceDetail(
    LoginRequiredMixin, ObjectPermissionRequiredMixin, DetailView
):
    model = Invoice
    permission_required = "change_challenge"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.challenge
