from django.urls import path

from grandchallenge.products.views import (
    AboutPage,
    CompanyDetail,
    CompanyList,
    ContactPage,
    ImportDataView,
    ProductDetail,
    ProductList,
)

app_name = "products"

urlpatterns = [
    path("", ProductList.as_view(), name="product-list"),
    path("companies/", CompanyList.as_view(), name="company-list"),
    path("about/", AboutPage.as_view(), name="about"),
    path("contact/", ContactPage.as_view(), name="contact"),
    path("product/<slug>/", ProductDetail.as_view(), name="product-detail"),
    path("company/<slug>/", CompanyDetail.as_view(), name="company-detail"),
    path("import-data/", ImportDataView.as_view(), name="import-data"),
]
