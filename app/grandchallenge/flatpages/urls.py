from django.urls import path


from grandchallenge.flatpages.views import (
    FlatPageCreate,
    FlatPageUpdate,
)

app_name = "flatpages"

urlpatterns = [
    path("create/", FlatPageCreate.as_view(), name="create"),
    path("<int:pk>/update/", FlatPageUpdate.as_view(), name="update"),
]
