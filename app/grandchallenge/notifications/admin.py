from actstream.models import Follow
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from grandchallenge.core.admin import (
    GroupObjectPermissionAdmin,
    UserObjectPermissionAdmin,
)
from grandchallenge.notifications.models import (
    FollowGroupObjectPermission,
    FollowUserObjectPermission,
    Notification,
    NotificationGroupObjectPermission,
    NotificationUserObjectPermission,
)


class MissingRequiredObjectsFilter(admin.SimpleListFilter):
    title = "missing required objects"
    parameter_name = "objects_missing"

    def lookups(self, request, model_admin):
        return [
            ("1", "Yes"),
        ]

    def queryset(self, request, queryset):
        if self.value() != "1":
            return queryset

        # For each GFK field, find notifications that reference a
        # non-existent object by checking existence per content type.
        dangling_pks = set()

        gfk_fields = [
            ("actor_content_type", "actor_object_id"),
            ("target_content_type", "target_object_id"),
            (
                "action_object_content_type",
                "action_object_object_id",
            ),
        ]

        # Collect all referenced content type IDs in a single pass
        all_ct_ids = set()
        for ct_field, _ in gfk_fields:
            all_ct_ids.update(
                queryset.filter(**{f"{ct_field}__isnull": False})
                .values_list(ct_field, flat=True)
                .distinct()
            )

        content_types = list(ContentType.objects.filter(pk__in=all_ct_ids))

        for ct_field, id_field in gfk_fields:
            for content_type in content_types:
                model_class = content_type.model_class()
                if model_class is None:
                    dangling_pks.update(
                        queryset.filter(
                            **{
                                ct_field: content_type,
                                f"{id_field}__isnull": False,
                            }
                        ).values_list("pk", flat=True)
                    )
                    continue

                # Get all object IDs referenced by notifications for
                # this content type
                referenced_ids = set(
                    queryset.filter(
                        **{
                            ct_field: content_type,
                            f"{id_field}__isnull": False,
                        }
                    ).values_list(id_field, flat=True)
                )

                if not referenced_ids:
                    continue

                # Find which of those IDs still exist
                existing_ids = set(
                    model_class.objects.filter(
                        pk__in=referenced_ids
                    ).values_list("pk", flat=True)
                )

                # IDs that are referenced but don't exist
                missing_ids = referenced_ids - {str(pk) for pk in existing_ids}

                if missing_ids:
                    dangling_pks.update(
                        queryset.filter(
                            **{
                                ct_field: content_type,
                                f"{id_field}__in": missing_ids,
                            }
                        ).values_list("pk", flat=True)
                    )

        return queryset.filter(pk__in=dangling_pks)


class FollowAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "user",
        "follow_object",
        "content_type",
        "flag",
        "actor_only",
        "started",
    )
    raw_id_fields = ("user", "content_type")
    list_select_related = ("user", "content_type")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    readonly_fields = ("user",)
    ordering = ("-created",)
    list_display = (
        "__str__",
        "type",
        "actor",
        "message",
        "action_object",
        "target",
        "read",
    )
    list_filter = ("type", "read", MissingRequiredObjectsFilter)
    raw_id_fields = (
        "actor_content_type",
        "target_content_type",
        "action_object_content_type",
    )
    search_fields = ("user__username",)
    list_select_related = (
        "user",
        "actor_content_type",
        "target_content_type",
        "action_object_content_type",
    )


admin.site.unregister(Follow)
admin.site.register(Follow, FollowAdmin)
admin.site.register(FollowUserObjectPermission, UserObjectPermissionAdmin)
admin.site.register(FollowGroupObjectPermission, GroupObjectPermissionAdmin)
admin.site.register(
    NotificationUserObjectPermission, UserObjectPermissionAdmin
)
admin.site.register(
    NotificationGroupObjectPermission, GroupObjectPermissionAdmin
)
