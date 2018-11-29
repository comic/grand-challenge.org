from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View


class IndexView(LoginRequiredMixin, View):  #TODO replace mixin with right authentication mixin
    def get(self, request):
        return render(request, "pages/home.html")

