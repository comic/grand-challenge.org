from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import now
from django.views.generic import ListView

from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import UserProfile


class NotificationList(LoginRequiredMixin, ListView):
    model = Notification

    def get_queryset(self):
        queryset = super().get_queryset()
        qs = queryset.filter(user__user_profile=self.request.user.user_profile)
        profile = self.request.user.user_profile
        Notification.objects.filter(
            user__user_profile=self.request.user.user_profile
        ).update(read=True)
        UserProfile.objects.filter(pk=profile.pk).update(
            notifications_last_read_at=now()
        )
        return qs
