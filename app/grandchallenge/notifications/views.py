from actstream.models import user_stream
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.views.generic import TemplateView


class NotificationList(LoginRequiredMixin, TemplateView):
    template_name = "notifications/notification_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        obj = self.request.user
        notifications = user_stream(obj=self.request.user)

        # Workaround for
        # https://github.com/justquick/django-activity-stream/issues/482
        notifications = notifications.exclude(
            actor_content_type=ContentType.objects.get_for_model(obj),
            actor_object_id=obj.pk,
        )

        context.update({"object_list": notifications})

        return context
