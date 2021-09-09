from actstream.models import Follow
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework import mixins, viewsets
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.core.filters import FilterMixin
from grandchallenge.notifications.filters import (
    FollowFilter,
    NotificationFilter,
)
from grandchallenge.notifications.forms import FollowForm
from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.serializers import (
    FollowSerializer,
    NotificationSerializer,
)
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
)
from grandchallenge.subdomains.utils import reverse


class NotificationViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = [ObjectPermissionsFilter]

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully deleted.",
        )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully updated.",
        )
        return response


class FollowViewSet(
    mixins.DestroyModelMixin,
    mixins.UpdateModelMixin,
    viewsets.ReadOnlyModelViewSet,
):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = [ObjectPermissionsFilter]

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Subscription successfully deleted.",
        )
        return response

    def perform_update(self, serializer):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Subscription successfully updated.",
        )
        return serializer.save()


class NotificationList(
    LoginRequiredMixin, FilterMixin, PermissionListMixin, ListView
):
    model = Notification
    permission_required = "view_notification"
    filter_class = NotificationFilter
    paginate_by = 50

    def get_queryset(self):
        return prefetch_generic_foreign_key_objects(
            super()
            .get_queryset()
            .select_related(
                "actor_content_type",
                "target_content_type",
                "action_object_content_type",
                "user__verification",
            )
            .order_by("-created")
        )


class FollowList(
    LoginRequiredMixin, FilterMixin, PermissionListMixin, ListView
):
    model = Follow
    permission_required = "view_follow"
    filter_class = FollowFilter
    paginate_by = 50

    def get_queryset(self, *args, **kwargs):
        return prefetch_generic_foreign_key_objects(
            super()
            .get_queryset()
            .select_related("user", "content_type")
            .order_by("content_type")
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
    form_class = FollowForm
    success_message = "Subscription successfully added"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse("notifications:follow-list")
