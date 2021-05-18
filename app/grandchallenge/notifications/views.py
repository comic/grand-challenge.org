from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import FormView, ListView

from grandchallenge.notifications.forms import NotificationForm
from grandchallenge.notifications.models import Notification
from grandchallenge.subdomains.utils import reverse, reverse_lazy


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
            {
                "notifications_last_read_at": profile.notifications_last_read_at,
                "mark_as_read_action": NotificationForm.MARK_READ,
                "mark_as_unread_action": NotificationForm.MARK_UNREAD,
                "delete_notification": NotificationForm.REMOVE,
            }
        )
        # TODO side-effect, not nice
        profile.update_notifications_last_read_timestep()
        return context


class NotificationUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = NotificationForm
    template_name = "notifications/notification_update_form.html"
    success_message = "Notification successfully updated"
    permission_required = "change_notification"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        return self.request.notification

    def get_success_url(self):
        return reverse("notifications:list",)

    def form_valid(self, form):
        form.update()
        return super().form_valid(form)
