from django.shortcuts import render_to_response
from rest_framework import permissions
from django.contrib.auth.mixins import LoginRequiredMixin
from config import settings
from grandchallenge.retina_api.mixins import RetinaAPIPermissionMixin
from django.views import View


class IndexView(RetinaAPIPermissionMixin, View):
    def get(self, request):
        context = {"LOGOUT_URL": settings.LOGOUT_URL}
        return render_to_response("pages/home.html", context)

