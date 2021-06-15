from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.query_utils import Q
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
    prefetch_notification_action,
)
from grandchallenge.subdomains.utils import reverse


class NotificationList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Notification
    permission_required = "view_notification"

    def get_queryset(self):
        return prefetch_notification_action(
            super().get_queryset().order_by("-created")
        )

    def post(self, request, *args, **kwargs):
        if "delete" in request.POST:
            action = "delete"
        elif "mark_read" in request.POST:
            action = "mark_read"
        elif "mark_unread" in request.POST:
            action = "mark_unread"

        selected_notifications = request.POST.getlist("checkbox")
        notifications = Notification.objects.filter(
            user=request.user, id__in=selected_notifications
        ).all()

        if not notifications:
            return HttpResponseForbidden()
        else:
            for notification in notifications:
                if notification.user != self.request.user:
                    return HttpResponseForbidden()
                if action == "delete":
                    notification.delete()
                elif action == "mark_read":
                    notification.read = True
                    notification.save()
                elif action == "mark_unread":
                    notification.read = False
                    notification.save()
            return HttpResponseRedirect(reverse("notifications:list"))


class FollowList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Follow
    permission_required = "view_follow"

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
            }
        )
        return context


class FollowDelete(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    SuccessMessageMixin,
    DeleteView,
):
    model = Follow
    success_message = "Subscription successfully deleted"
    permission_required = "delete_follow"
    raise_exception = True

    def get_permission_object(self):
        return self.get_object()

    def get_success_url(self):
        return reverse("notifications:follow-list")


class FollowCreate(
    LoginRequiredMixin, SuccessMessageMixin, CreateView,
):
    model = Follow
    fields = ["user", "content_type", "object_id", "actor_only"]
    success_message = "Subscription successfully added"

    def get_success_url(self):
        return reverse("notifications:follow-list")
