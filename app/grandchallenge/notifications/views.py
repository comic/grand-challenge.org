from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import now
from django.views.generic import TemplateView

from grandchallenge.profiles.models import UserProfile


class NotificationList(LoginRequiredMixin, TemplateView):
    template_name = "notifications/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        profile = self.request.user.user_profile

        context.update(
            {
                "notifications_last_read_at": profile.notifications_last_read_at,
                "object_list": profile.notifications,
            }
        )

        UserProfile.objects.filter(pk=profile.pk).update(
            notifications_last_read_at=now()
        )

        return context
