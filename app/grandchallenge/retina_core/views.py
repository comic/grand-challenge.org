from django.shortcuts import render
from rest_framework import permissions
from django.contrib.auth.mixins import LoginRequiredMixin
from grandchallenge.retina_api.mixins import RetinaAPIPermissionMixin
from django.views import View


class IndexView(RetinaAPIPermissionMixin, View):
    def get(self, request):
        return render(request, "pages/home.html")

