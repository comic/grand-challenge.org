from django.views.generic import ListView
from guardian.mixins import LoginRequiredMixin
from knox.models import AuthToken


class APITokenList(LoginRequiredMixin, ListView):
    model = AuthToken

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).prefetch_related(
            "session_set"
        )
