from django.urls import path, re_path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path('worklist_groups/', views.WorklistGroupTable.as_view(), name="worklist_groups"),
    re_path(r'^worklist_groups/(?P<pk>[0-9]+)$', views.WorklistGroupRecord.as_view(), name="worklist_group"),
    path('worklists/', views.WorklistTable.as_view(), name="worklists"),
    re_path(r'^worklists/(?P<pk>[0-9]+)$', views.WorklistRecord.as_view(), name="worklist")
]
