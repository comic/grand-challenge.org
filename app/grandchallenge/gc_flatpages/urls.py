from django.contrib.flatpages import views
from django.urls import path, re_path


from grandchallenge.gc_flatpages.views import (
    FlatPageCreate,
    FlatPageUpdate,
)

app_name = "gc_flatpages"

urlpatterns = [
    path("create/", FlatPageCreate.as_view(), name="create"),
    path("<int:pk>/update/", FlatPageUpdate.as_view(), name="update"),
]

urlpatterns += [
    re_path(r"^(?P<url>.*/)$", views.flatpage),
]
