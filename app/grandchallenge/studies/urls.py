from django.urls import path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path("studies/", views.StudyTable.as_view(), name="studies"),
    path("studies/<uuid:pk>/", views.StudyRecord.as_view(), name="study"),
    path("studies/list/", views.StudyList.as_view(), name="study-list"),
    path("studies/create/", views.StudyCreate.as_view(), name="study-create"),
    path("studies/update/<uuid:pk>/", views.StudyUpdate.as_view(), name="study-update"),
    path("studies/delete/<uuid:pk>/", views.StudyDelete.as_view(), name="study-delete"),
]
