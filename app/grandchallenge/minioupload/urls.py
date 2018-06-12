# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.minioupload.views import (
    EvaporateFileUpload, presign_string,
)

app_name = 'minioupload'

urlpatterns =[
    path('presign/', presign_string, name='presign'),
    path('upload/', EvaporateFileUpload.as_view(), name='upload'),
]
