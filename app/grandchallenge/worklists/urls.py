from django.urls import path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path("worklists/worklists/", views.WorklistTable.as_view(), name="worklists"),
    path("worklists/worklists/<uuid:pk>/", views.WorklistRecord.as_view(), name="worklist"),
    path("worklists/worklists/list/", views.WorklistList.as_view(), name="worklist-list"),
    path("worklists/worklists/create/", views.WorklistCreate.as_view(), name="worklist-create"),
    path("worklists/worklists/update/<uuid:pk>/", views.WorklistUpdate.as_view(), name="worklist-update"),
    path("worklists/worklists/delete/<uuid:pk>/", views.WorklistDelete.as_view(), name="worklist-delete"),
    path("worklists/sets/", views.WorklistSetTable.as_view(), name="sets"),
    path("worklists/sets/<uuid:pk>/", views.WorklistSetRecord.as_view(), name="set"),
    path("worklists/sets/list/", views.WorklistSetList.as_view(), name="set-list"),
    path("worklists/sets/create/", views.WorklistSetCreate.as_view(), name="set-create"),
    path("worklists/sets/update/<uuid:pk>/", views.WorklistSetUpdate.as_view(), name="set-update"),
    path("worklists/sets/delete/<uuid:pk>/", views.WorklistSetDelete.as_view(), name="set-delete"),
]
