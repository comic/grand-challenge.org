from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from grandchallenge.notifications.models import Notification


class NotificationList(LoginRequiredMixin, ListView):
    model = Notification

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .order_by("-action__timestamp")
        )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        profile = self.request.user.user_profile
        context.update(
            {"notifications_last_read_at": profile.notifications_last_read_at}
        )
        # TODO side-effect, not nice
        profile.update_notifications_last_read_timestep()
        return context
