from django.urls import path

from grandchallenge.ai_website.views import (
    AboutPage,
    CompanyList,
    CompanyPage,
    ContactPage,
    ImportDataView,
    ProductList,
    ProductPage,
)


app_name = "ai-website"

urlpatterns = [
    path("", ProductList.as_view(), name="product_list"),
    path("companies/", CompanyList.as_view(), name="company_list"),
    path("about/", AboutPage.as_view(), name="about"),
    path("contact/", ContactPage.as_view(), name="contact"),
    path("product/<int:pk>/", ProductPage.as_view(), name="product_page"),
    path("company/<int:pk>/", CompanyPage.as_view(), name="company_page"),
    path("import-data/", ImportDataView.as_view(), name="import-data"),
]
