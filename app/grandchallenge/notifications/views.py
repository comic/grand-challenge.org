from actstream.models import Follow
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import (
    HttpResponseNotFound,
    HttpResponseRedirect,
)
from django.template.defaultfilters import pluralize
from django.views.generic import CreateView, DeleteView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from guardian.shortcuts import get_objects_for_user

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
    prefetch_nested_generic_foreign_key_objects,
)
from grandchallenge.subdomains.utils import reverse


class NotificationList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Notification
    permission_required = "view_notification"
    paginate_by = 50

    def get_queryset(self):
        return prefetch_nested_generic_foreign_key_objects(
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
        notifications = get_objects_for_user(
            request.user,
            ["delete_notification", "change_notification"],
            Notification,
        ).filter(id__in=selected_notifications)
        notifications_count = notifications.count()
        if not notifications:
            return HttpResponseNotFound()
        else:
            if action == "delete":
                notifications.delete()
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"{notifications_count} notification{pluralize(notifications_count)} successfully deleted.",
                )
            elif action == "mark_read":
                notifications.update(read=True)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"{notifications_count} notificiation{pluralize(notifications_count)} successfully marked as read.",
                )
            elif action == "mark_unread":
                notifications.update(read=False)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    f"{notifications_count} notification{pluralize(notifications_count)} successfully marked as unread.",
                )
            return HttpResponseRedirect(reverse("notifications:list"))


class FollowList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Follow
    permission_required = "view_follow"

    def get_queryset(self, *args, **kwargs):
        return prefetch_generic_foreign_key_objects(
            super().get_queryset().select_related("user")
        )


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
