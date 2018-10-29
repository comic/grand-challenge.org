from django.urls import path, re_path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path('studies/create/', views.StudyCreate.as_view(), name="study_create"),
    path('studies/<int:pk>/update/', views.StudyUpdate.as_view(), name="study_update"),
    path('studies/<int:pk>/delete/', views.StudyDelete.as_view(), name="study_delete"),
    path('studies/', views.StudyTable.as_view(), name="studies"),
    re_path(r'^studies/(?P<pk>[0-9]+)$', views.StudyRecord.as_view(), name="study")
]