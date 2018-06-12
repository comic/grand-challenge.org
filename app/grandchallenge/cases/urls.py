# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.views import CaseCreate, CaseUpdate, CaseDetail

app_name = 'cases'

urlpatterns = [
    path('create/', CaseCreate.as_view(), name='create'),
    path('<uuid:pk>/', CaseDetail.as_view(), name='detail'),
    path('<uuid:pk>/update/', CaseUpdate.as_view(), name='update'),
]
