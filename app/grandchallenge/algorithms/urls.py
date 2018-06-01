# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.algorithms.forms import algorithm_upload_widget
from grandchallenge.algorithms.views import (
    AlgorithmList, AlgorithmCreate, AlgorithmDetail
)
from grandchallenge.cases.forms import case_upload_widget

app_name = 'algorithms'

urlpatterns = [
    path('', AlgorithmList.as_view(), name='list'),
    path('create/', AlgorithmCreate.as_view(), name='create'),
    path(
        f'create/{algorithm_upload_widget.ajax_target_path}',
        case_upload_widget.handle_ajax,
        name='upload-ajax',
    ),
    path('<uuid:pk>/', AlgorithmDetail.as_view(), name='detail'),
]
