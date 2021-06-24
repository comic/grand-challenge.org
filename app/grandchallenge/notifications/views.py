from actstream.models import Follow
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView, ListView
from guardian.mixins import (
    LoginRequiredMixin,
    PermissionListMixin,
    PermissionRequiredMixin as ObjectPermissionRequiredMixin,
)
from rest_framework import status, viewsets
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework_guardian.filters import ObjectPermissionsFilter

from grandchallenge.notifications.forms import FollowForm
from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.serializers import NotificationSerializer
from grandchallenge.notifications.utils import (
    prefetch_generic_foreign_key_objects,
    prefetch_nested_generic_foreign_key_objects,
)
from grandchallenge.subdomains.utils import reverse


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = (DjangoObjectPermissions,)
    filter_backends = [ObjectPermissionsFilter]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully deleted.",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully updated.",
        )

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class NotificationList(LoginRequiredMixin, PermissionListMixin, ListView):
    model = Notification
    permission_required = "view_notification"
    paginate_by = 50

    def get_queryset(self):
        return prefetch_nested_generic_foreign_key_objects(
            super().get_queryset().order_by("-created")
        )


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
    form_class = FollowForm
    success_message = "Subscription successfully added"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse("notifications:follow-list")
