from django.urls import path

from grandchallenge.worklists.views import (
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
    path("<uuid:pk>/detail/", WorklistDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", WorklistUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", WorklistDeleteView.as_view(), name="delete"),
]
