from django.conf.urls import include
from django.urls import path


urlpatterns = [
    path("", include("grandchallenge.ai_website.urls")),
]
