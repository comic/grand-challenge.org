# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.datasets.views import (
    ImageSetList,
    ImageSetCreate,
    ImageSetDetail,
)

app_name = "datasets"

urlpatterns = [
    path("", ImageSetList.as_view(), name="imageset-list"),
    path("create/", ImageSetCreate.as_view(), name="imageset-create"),
    path("<uuid:pk>/", ImageSetDetail.as_view(), name="imageset-detail"),
]
