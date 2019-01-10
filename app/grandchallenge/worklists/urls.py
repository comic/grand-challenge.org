from django.urls import path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path("worklist/", views.WorklistTable.as_view(), name="worklists"),
    path(
        "worklist/<uuid:pk>/", views.WorklistRecord.as_view(), name="worklist"
    ),
    path(
        "worklist/create/",
        views.WorklistCreateView.as_view(),
        name="worklist-create",
    ),
    path(
        "worklist/remove/<uuid:pk>/",
        views.WorklistRemoveView.as_view(),
        name="worklist-remove",
    ),
    path(
        "worklist/update/<uuid:pk>/",
        views.WorklistUpdateView.as_view(),
        name="worklist-update",
    ),
    path(
        "worklist/display/",
        views.WorklistDisplayView.as_view(),
        name="worklist-display",
    ),
    path("set/", views.WorklistSetTable.as_view(), name="sets"),
    path("set/<uuid:pk>/", views.WorklistSetRecord.as_view(), name="set"),
    path(
        "set/create/", views.WorklistSetCreateView.as_view(), name="set-create"
    ),
    path(
        "set/remove/<uuid:pk>/",
        views.WorklistSetRemoveView.as_view(),
        name="set-remove",
    ),
    path(
        "set/update/<uuid:pk>/",
        views.WorklistSetUpdateView.as_view(),
        name="set-update",
    ),
    path(
        "set/display/",
        views.WorklistSetDisplayView.as_view(),
        name="set-display",
    ),
]
