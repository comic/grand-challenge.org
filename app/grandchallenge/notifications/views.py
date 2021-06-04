from actstream.models import Follow
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.views.generic import FormView, ListView
from guardian.mixins import (
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.notifications.forms import (
    NotificationForm,
    SubscriptionForm,
)
from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
    prefetch_notification_action,
)
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class NotificationList(LoginRequiredMixin, ListView):
    model = Notification

    def get_queryset(self):
        return prefetch_notification_action(
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

    def post(self, request, *args, **kwargs):
        if "delete" in request.POST:
            action = "delete"
        elif "mark_read" in request.POST:
            action = "mark_read"
        elif "mark_unread" in request.POST:
            action = "mark_unread"

        selected_notifications = request.POST.getlist("checkbox")
        if action == "delete":
            Notification.objects.filter(
                user=request.user, id__in=selected_notifications
            ).delete()
        elif action == "mark_read":
            notifications = Notification.objects.filter(
                user=request.user, id__in=selected_notifications
            ).all()
            for notification in notifications:
                notification.read = True
                notification.save()
        elif action == "mark_unread":
            notifications = Notification.objects.filter(
                user=request.user, id__in=selected_notifications
            ).all()
            for notification in notifications:
                notification.read = False
                notification.save()
        return HttpResponseRedirect(reverse("notifications:list"))


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
        form = self.get_form()
        form.full_clean()
        return form.cleaned_data["notification"]

    def get_success_url(self):
        return reverse("notifications:list")

    def form_valid(self, form):
        form.update()
        return super().form_valid(form)


class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Follow

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "followed_topics": prefetch_generic_foreign_key_objects(
                    Follow.objects.filter(
                        Q(user=self.request.user)
                        & Q(
                            content_type=ContentType.objects.get(
                                app_label="forum_conversation", model="topic"
                            ).id
                        )
                    ).select_related("user")
                ),
                "followed_forums": prefetch_generic_foreign_key_objects(
                    Follow.objects.filter(
                        Q(user=self.request.user)
                        & Q(
                            content_type=ContentType.objects.get(
                                app_label="forum", model="forum"
                            ).id
                        )
                    ).select_related("user")
                ),
                "followed_users": prefetch_generic_foreign_key_objects(
                    Follow.objects.filter(
                        Q(user=self.request.user)
                        & Q(
                            content_type=ContentType.objects.get(
                                app_label="auth", model="user"
                            ).id
                        )
                    ).select_related("user")
                ),
            }
        )
        return context


class SubscriptionDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    FormView,
):
    form_class = SubscriptionForm
    template_name = "notifications/subscription_update_form.html"
    success_message = "Subscription successfully deleted"
    permission_required = "change_follow"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_permission_object(self):
        form = self.get_form()
        form.full_clean()
        return form.cleaned_data["subscription_object"]

    def get_success_url(self):
        return reverse("notifications:subscriptions-list")

    def form_valid(self, form):
        form.unfollow()
        return super().form_valid(form)


class SubscriptionCreate(
    LoginRequiredMixin, SuccessMessageMixin, FormView,
):
    form_class = SubscriptionForm
    template_name = "notifications/subscription_update_form.html"
    success_message = "Subscription successfully added"
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        return reverse("notifications:subscriptions-list")

    def form_valid(self, form):
        form.follow()
        return super().form_valid(form)
