from django.urls import path

from grandchallenge.invoices.views import InvoiceList

app_name = "invoices"

urlpatterns = [
    path("", InvoiceList.as_view(), name="list"),
]
