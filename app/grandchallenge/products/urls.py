from django.urls import path

from grandchallenge.products.views import (
    AboutAddProductPage,
    AboutPage,
    CompanyDetail,
    CompanyList,
    ContactPage,
    FaqPage,
    ImportDataView,
    ProductDetail,
    ProductList,
    ProductsPostCreate,
    ProductsPostDetail,
    ProductsPostList,
    ProductsPostUpdate,
    ProjectAirForm,
    ProjectAirPage,
)

app_name = "products"

urlpatterns = [
    path("", ProductList.as_view(), name="product-list"),
    path("companies/", CompanyList.as_view(), name="company-list"),
    path("about/", AboutPage.as_view(), name="about"),
    path("about/faq", FaqPage.as_view(), name="about-faq"),
    path(
        "about/add-product",
        AboutAddProductPage.as_view(),
        name="about-add-product",
    ),
    path("contact/", ContactPage.as_view(), name="contact"),
    path("project-air/", ProjectAirPage.as_view(), name="project-air"),
    path("product/<slug>/", ProductDetail.as_view(), name="product-detail"),
    path("company/<slug>/", CompanyDetail.as_view(), name="company-detail"),
    path("import-data/", ImportDataView.as_view(), name="import-data"),
    path(
        "project-air-files/",
        ProjectAirForm.as_view(),
        name="project-air-files",
    ),
    path("blogs/", ProductsPostList.as_view(), name="blogs-list"),
    path("blogs/create/", ProductsPostCreate.as_view(), name="blogs-create"),
    path("blogs/<slug>/", ProductsPostDetail.as_view(), name="blogs-detail"),
    path(
        "blogs/<slug>/update/",
        ProductsPostUpdate.as_view(),
        name="blogs-update",
    ),
]
