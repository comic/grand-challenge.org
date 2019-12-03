from django.urls import path

from grandchallenge.ai_website.views import HomeTemplate


urlpatterns = [
    path("", HomeTemplate.as_view(), name="home"),
]
