# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.views import CaseCreate

app_name = 'cases'

urlpatterns = [
    path('create/', CaseCreate.as_view(), name='create'),
]
