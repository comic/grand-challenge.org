from django.urls import path
from grandchallenge.studies import views

app_name = "studies"
urlpatterns = [
    path("studies/", views.StudyTable.as_view(), name="studies"),
    path("studies/<uuid:pk>/", views.StudyRecord.as_view(), name="study"),
    path("studies/create/", views.StudyCreateView.as_view(), name="study-create"),
    path("studies/remove/<uuid:pk>/", views.StudyRemoveView.as_view(), name="study-remove"),
    path("studies/update/<uuid:pk>/", views.StudyUpdateView.as_view(), name="study-update"),
    path("studies/display/", views.StudyDisplayView.as_view(), name="study-display"),
]
