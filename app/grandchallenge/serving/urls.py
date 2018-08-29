# -*- coding: utf-8 -*-
from django.urls import path

from grandchallenge.serving.views import serve_folder

app_name = "serving"

urlpatterns = [
    path("images/<path:path>", serve_folder, {"folder": "images"}),
    path("logos/<path:path>", serve_folder, {"folder": "logos"}),
    path("banners/<path:path>", serve_folder, {"folder": "banners"}),
    path("mugshots/<path:path>", serve_folder, {"folder": "mugshots"}),
    path("favicon/<path:path>", serve_folder, {"folder": "favicon"}),
    path(
        "evaluation-supplementary/<path:path>",
        serve_folder,
        {"folder": "evaluation-supplementary"},
    ),
    path(
        "<slug:challenge_short_name>/<path:path>",
        serve_folder,
        name="challenge-file",
    ),
]
