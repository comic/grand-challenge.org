# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.minioupload.views import presigned_url, MinioFileUpload

urlpatterns =[
    path('presign/<path:filename>/', presigned_url),
    path('upload/', MinioFileUpload.as_view())
]
