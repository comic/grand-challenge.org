from django.urls import path

from grandchallenge.workspaces.views import WorkspaceCreate, WorkspaceList

app_name = "workspaces"

urlpatterns = [
    path("", WorkspaceList.as_view(), name="list"),
    path("<slug>/create/", WorkspaceCreate.as_view(), name="create"),
]
