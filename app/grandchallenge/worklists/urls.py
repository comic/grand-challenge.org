from django.urls import path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path("list/", views.WorklistTable.as_view(), name="list"),
    path("list/<uuid:pk>/", views.WorklistRecord.as_view(), name="list"),
    path(
        "list/create/", views.WorklistCreateView.as_view(), name="list-create"
    ),
    path(
        "list/remove/<uuid:pk>/",
        views.WorklistRemoveView.as_view(),
        name="list-remove",
    ),
    path(
        "list/update/<uuid:pk>/",
        views.WorklistUpdateView.as_view(),
        name="list-update",
    ),
    path(
        "list/display/",
        views.WorklistDisplayView.as_view(),
        name="list-display",
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
