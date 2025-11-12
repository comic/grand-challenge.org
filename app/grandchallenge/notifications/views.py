from actstream.models import Follow
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.views.generic import CreateView, DeleteView, ListView
from guardian.mixins import LoginRequiredMixin
from rest_framework import mixins, viewsets
from rest_framework.permissions import DjangoObjectPermissions

from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    ViewObjectPermissionsFilter,
)
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
    filter_backends = [ViewObjectPermissionsFilter]

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully deleted."
        )
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Notifications successfully updated."
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
    filter_backends = [ViewObjectPermissionsFilter]

    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request, *args, **kwargs)
        messages.add_message(
            request, messages.SUCCESS, "Subscription successfully deleted."
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
    LoginRequiredMixin, FilterMixin, ViewObjectPermissionListMixin, ListView
):
    model = Notification
    filter_class = NotificationFilter
    paginate_by = 50

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related(
                "actor_content_type",
                "target_content_type",
                "action_object_content_type",
                "user__verification",
            )
            .order_by("-created")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prefetch the object list here as at this point it has been paginated
        # which saves prefetching the related objects for all notifications
        context["object_list"] = prefetch_generic_foreign_key_objects(
            context["object_list"]
        )

        return context


class FollowList(
    LoginRequiredMixin, FilterMixin, ViewObjectPermissionListMixin, ListView
):
    model = Follow
    filter_class = FollowFilter
    paginate_by = 50

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .exclude(
                Q(
                    content_type__app_label="archives",
                    content_type__model="archivepermissionrequest",
                )
                | Q(
                    content_type__app_label="algorithms",
                    content_type__model="algorithmpermissionrequest",
                )
                | Q(
                    content_type__app_label="reader_studies",
                    content_type__model="readerstudypermissionrequest",
                )
                | Q(
                    content_type__app_label="participants",
                    content_type__model="registrationrequest",
                )
                | Q(
                    content_type__app_label="cases",
                    content_type__model="rawimageuploadsession",
                )
            )
            .exclude(flag="job-inactive")
            .filter(user=self.request.user)
            .select_related("user", "content_type")
            .order_by("content_type")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Prefetch the object list here as at this point it has been paginated
        # which saves prefetching the related objects for all notifications
        context["object_list"] = prefetch_generic_foreign_key_objects(
            context["object_list"]
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


class FollowCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Follow
    form_class = FollowForm
    success_message = "Subscription successfully added"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse("notifications:follow-list")
