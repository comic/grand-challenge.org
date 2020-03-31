from django.urls import path

from grandchallenge.overview_pages.views import OverviewPageDetail

app_name = "overview_pages"

urlpatterns = [
    path("<slug>/", OverviewPageDetail.as_view(), name="detail"),
]
