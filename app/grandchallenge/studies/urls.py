from django.urls import path, re_path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path('studies/', views.StudyTable.as_view(), name="studies"),
    path('studies/<int:pk>/', views.StudyRecord.as_view(), name="study"),
    path('studies/list/', views.Studyist.as_view(), name="study_list"),
    path('studies/create/', views.StudyCreate.as_view(), name="study_create"),
    path('studies/update/<int:pk>/', views.StudyUpdate.as_view(), name="study_update"),
    path('studies/delete/<int:pk>/', views.StudyDelete.as_view(), name="study_delete"),
]