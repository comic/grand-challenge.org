# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.algorithms.views import AlgorithmList, AlgorithmCreate

app_name = 'algorithms'

urlpatterns = [
    path('', AlgorithmList.as_view(), name='list'),
    path('create/', AlgorithmCreate.as_view(), name='create'),
]
