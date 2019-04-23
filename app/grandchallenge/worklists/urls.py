from django.urls import path
from grandchallenge.worklists.views_forms import (
    WorklistListView,
    WorklistCreateView,
    WorklistDetailView,
    WorklistDeleteView,
    WorklistUpdateView,
)

app_name = "worklists"
urlpatterns = [
    path("", WorklistListView.as_view(), name="list"),
    path("create/", WorklistCreateView.as_view(), name="create"),
    path("<uuid:pk>/detail/", WorklistDeleteView.as_view(), name="detail"),
    path("<uuid:pk>/delete/", WorklistDeleteView.as_view(), name="remove"),
    path("<uuid:pk>/update/", WorklistUpdateView.as_view(), name="update"),
]
