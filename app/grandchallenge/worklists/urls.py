from django.urls import path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path("worklists/worklists/", views.WorklistTable.as_view(), name="worklists"),
    path("worklists/worklists/<uuid:pk>/", views.WorklistRecord.as_view(), name="worklist"),
    path("worklists/worklists/create/", views.WorklistCreateView.as_view(), name="worklist-create"),
    path("worklists/worklists/remove/<uuid:pk>/", views.WorklistRemoveView.as_view(), name="worklist-remove"),
    path("worklists/worklists/update/<uuid:pk>/", views.WorklistUpdateView.as_view(), name="worklist-update"),
    path("worklists/worklists/display/", views.WorklistDisplayView.as_view(), name="worklist-display"),
    path("worklists/sets/", views.WorklistSetTable.as_view(), name="sets"),
    path("worklists/sets/<uuid:pk>/", views.WorklistSetRecord.as_view(), name="set"),
    path("worklists/sets/create/", views.WorklistSetCreateView.as_view(), name="set-create"),
    path("worklists/sets/remove/<uuid:pk>/", views.WorklistSetRemoveView.as_view(), name="set-remove"),
    path("worklists/sets/update/<uuid:pk>/", views.WorklistSetUpdateView.as_view(), name="set-update"),
    path("worklists/sets/display/", views.WorklistSetDisplayView.as_view(), name="set-display"),
]
