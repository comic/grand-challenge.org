# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.algorithms.forms import algorithm_upload_widget
from grandchallenge.algorithms.views import (
    AlgorithmList,
    AlgorithmCreate,
    AlgorithmDetail,
    JobList,
    JobCreate,
    JobDetail,
    ResultList,
    ResultDetail,
)

app_name = "algorithms"

urlpatterns = [
    path("", AlgorithmList.as_view(), name="list"),
    path("create/", AlgorithmCreate.as_view(), name="create"),
    path("<uuid:pk>/", AlgorithmDetail.as_view(), name="detail"),
    path("jobs/", JobList.as_view(), name="jobs-list"),
    path("jobs/create/", JobCreate.as_view(), name="jobs-create"),
    path("jobs/<uuid:pk>/", JobDetail.as_view(), name="jobs-detail"),
    path("results/", ResultList.as_view(), name="results-list"),
    path("results/<uuid:pk>/", ResultDetail.as_view(), name="results-detail"),
]
