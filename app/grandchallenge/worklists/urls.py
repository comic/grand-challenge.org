from django.urls import path, re_path
from grandchallenge.worklists import views

app_name = "worklists"
urlpatterns = [
    path('worklists/sets/', views.WorklistSetTable.as_view(), name="sets"),
    path('worklists/sets/<int:pk>/', views.WorklistSetRecord.as_view(), name="set"),
    path('worklists/sets/list/', views.WorklistSetList.as_view(), name="set_list"),
    path('worklists/sets/create/', views.WorklistSetCreate.as_view(), name="set_create"),
    path('worklists/sets/update/<int:pk>/', views.WorklistSetUpdate.as_view(), name="set_update"),
    path('worklists/sets/delete/<int:pk>/', views.WorklistSetDelete.as_view(), name="set_delete"),
]
