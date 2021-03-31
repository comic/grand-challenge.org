from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class NotificationList(LoginRequiredMixin, TemplateView):
    template_name = "notifications/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "object_list": self.request.user.notification_preference.notifications
            }
        )

        return context
