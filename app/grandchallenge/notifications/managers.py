from actstream.managers import ActionManager as ActstreamManager
from actstream.managers import stream
from actstream.registry import check
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


class ActionManager(ActstreamManager):
    @stream
    def user(
        self,
        obj,
        with_user_activity=False,
        follow_flag=None,
        since_following=False,
        **kwargs,
    ):
        """Create a stream of the most recent actions by objects that the user is following."""
        q = Q()
        qs = self.public()

        if not obj:
            return qs.none()

        check(obj)

        if with_user_activity:
            q = q | Q(
                actor_content_type=ContentType.objects.get_for_model(obj),
                actor_object_id=obj.pk,
            )

        follows = apps.get_model("actstream", "follow").objects.filter(
            user=obj
        )
        if follow_flag:
            follows = follows.filter(flag=follow_flag)

        content_types = ContentType.objects.filter(
            pk__in=follows.values("content_type_id")
        )

        if not (content_types.exists() or with_user_activity):
            return qs.none()

        for content_type in content_types:
            object_ids = follows.filter(content_type=content_type)

            if since_following:
                # Workaround for
                # https://github.com/justquick/django-activity-stream/issues/411
                q_kwargs = {"timestamp__gte": object_ids.values("started")}
            else:
                q_kwargs = {}

            q = (
                q
                | Q(
                    actor_content_type=content_type,
                    actor_object_id__in=object_ids.values("object_id"),
                    **q_kwargs,
                )
                | Q(
                    target_content_type=content_type,
                    target_object_id__in=object_ids.filter(
                        actor_only=False
                    ).values("object_id"),
                    **q_kwargs,
                )
                | Q(
                    action_object_content_type=content_type,
                    action_object_object_id__in=object_ids.filter(
                        actor_only=False
                    ).values("object_id"),
                    **q_kwargs,
                )
            )

        return qs.filter(q, **kwargs)
