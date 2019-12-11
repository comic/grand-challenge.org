from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path


urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path(
        "", include("grandchallenge.ai_website.urls", namespace="ai-website")
    ),
]
