# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.cases.forms import case_upload_widget, \
    upload_raw_files_widget
from grandchallenge.cases.views import CaseList, CaseCreate, CaseDetail, \
    UploadRawFiles

app_name = 'cases'

urlpatterns = [
    path('', CaseList.as_view(), name='list'),
    path('create/', CaseCreate.as_view(), name='create'),
    path(
        f'create/{case_upload_widget.ajax_target_path}',
        case_upload_widget.handle_ajax,
        name='upload-ajax',
    ),
    path('<uuid:pk>/', CaseDetail.as_view(), name='detail'),

    path('new/upload/', UploadRawFiles.as_view(), name='create'),
    path(
        f"new/upload/{upload_raw_files_widget.ajax_target_path}",
        upload_raw_files_widget.handle_ajax,
        name="upload-raw-image-files-ajax",
    ),

    # TODO: Remove this - for testing purposes only!
    path('sth/', CaseList.as_view(), name='raw-files-session-detail'),
]
