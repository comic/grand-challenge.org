from django.urls import path

from grandchallenge.invoices.views import InvoiceDetail, InvoiceList

app_name = "invoices"

urlpatterns = [
    path("", InvoiceList.as_view(), name="list"),
    path(
        "<int:pk>/",
        InvoiceDetail.as_view(),
        name="detail",
    ),
]
