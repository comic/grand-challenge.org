from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from grandchallenge.notifications.models import Notification, NotificationType


class Command(BaseCommand):
    def handle(self, *args, **options):  # noqa: C901
        num_notifications = 0
        total_notification = Notification.objects.all().count()

        for notification in Notification.objects.filter(type="GENERIC").all():
            if (
                notification.action.actor_content_type.model == "user"
                and notification.action.target
            ):
                if notification.action.target_content_type.model == "forum":
                    notification.type = (
                        NotificationType.NotificationTypeChoices.FORUM_POST
                    )
                    notification.actor_content_type = (
                        notification.action.actor_content_type
                    )
                    notification.target_content_type = (
                        notification.action.target_content_type
                    )
                    notification.action_object_content_type = (
                        notification.action.action_object_content_type
                    )
                    notification.actor_object_id = (
                        notification.action.actor_object_id
                    )
                    notification.target_object_id = (
                        notification.action.target_object_id
                    )
                    notification.action_object_object_id = (
                        notification.action.action_object_object_id
                    )
                    notification.message = notification.action.verb
                    notification.save()
                    num_notifications += 1
                elif (
                    notification.action.target_content_type.model == "topic"
                    or notification.action.target_content_type.model
                    == "algorithm"
                    or notification.action.target_content_type.model
                    == "archive"
                    or notification.action.target_content_type.model
                    == "readerstudy"
                    or notification.action.target_content_type.model
                    == "challenge"
                ):
                    if (
                        notification.action.target_content_type.model
                        == "topic"
                    ):
                        notification.type = (
                            NotificationType.NotificationTypeChoices.FORUM_POST_REPLY
                        )
                    else:
                        notification.type = (
                            NotificationType.NotificationTypeChoices.ACCESS_REQUEST
                        )
                    notification.actor_content_type = (
                        notification.action.actor_content_type
                    )
                    notification.target_content_type = (
                        notification.action.target_content_type
                    )
                    notification.actor_object_id = (
                        notification.action.actor_object_id
                    )
                    notification.target_object_id = (
                        notification.action.target_object_id
                    )
                    notification.message = notification.action.verb
                    notification.save()
                    num_notifications += 1
            elif (
                notification.action.actor_content_type.model == "user"
                and notification.action.action_object
            ):
                notification.type = (
                    NotificationType.NotificationTypeChoices.NEW_ADMIN
                )
                notification.action_object_content_type = (
                    notification.action.actor_content_type
                )
                notification.action_object_object_id = (
                    notification.action.actor_object_id
                )
                notification.target_object_id = (
                    notification.action.action_object_object_id
                )
                notification.target_content_type = (
                    notification.action.action_object_content_type
                )
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
            elif "request" in notification.action.actor_content_type.model:
                notification.type = (
                    NotificationType.NotificationTypeChoices.REQUEST_UPDATE
                )
                notification.target_object_id = (
                    notification.action.actor_object_id
                )
                notification.target_content_type = (
                    notification.action.actor_content_type
                )
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
            elif notification.action.actor_content_type.model == "evaluation":
                notification.type = (
                    NotificationType.NotificationTypeChoices.EVALUATION_STATUS
                )
                notification.actor_content_type = ContentType.objects.filter(
                    model="user"
                ).get()
                notification.actor_object_id = (
                    notification.action.actor.submission.creator.pk
                )
                notification.action_object_object_id = (
                    notification.action.actor_object_id
                )
                notification.action_object_content_type = (
                    notification.action.actor_content_type
                )
                notification.target_object_id = (
                    notification.action.target_object_id
                )
                notification.target_content_type = (
                    notification.action.target_content_type
                )
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
            elif notification.action.actor_content_type.model == "submission":
                notification.type = (
                    NotificationType.NotificationTypeChoices.MISSING_METHOD
                )
                notification.actor_content_type = ContentType.objects.filter(
                    model="user"
                ).get()
                notification.actor_object_id = (
                    notification.action.actor.creator.pk
                )
                notification.action_object_content_type = (
                    notification.action.actor_content_type
                )
                notification.action_object_object_id = (
                    notification.action.actor_object_id
                )
                notification.target_content_type = (
                    notification.action.target_content_type
                )
                notification.target_object_id = (
                    notification.action.target_object_id
                )
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
            elif notification.action.actor_content_type.model == "algorithm":
                notification.type = (
                    NotificationType.NotificationTypeChoices.JOB_STATUS
                )
                notification.actor_content_type = (
                    notification.action.target_content_type
                )
                notification.actor_object_id = (
                    notification.action.target_object_id
                )
                notification.target_content_type = (
                    notification.action.actor_content_type
                )
                notification.target_object_id = (
                    notification.action.actor_object_id
                )
                notification.description = notification.action.description
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
            elif (
                notification.action.actor_content_type.model
                == "rawimageuploadsession"
            ):
                notification.type = (
                    NotificationType.NotificationTypeChoices.IMAGE_IMPORT_STATUS
                )
                notification.action_object_content_type = (
                    notification.action.actor_content_type
                )
                notification.action_object_object_id = (
                    notification.action.actor_object_id
                )
                notification.message = notification.action.verb
                notification.save()
                num_notifications += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"{num_notifications} of {total_notification} notifications processed."
            )
        )
