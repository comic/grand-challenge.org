from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import transaction
from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.utils import get_group_obj_perms_model, get_user_obj_perms_model


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--app-label", type=str)
        parser.add_argument("--model-name", type=str)

    def handle(self, *args, **options):
        app_label = options["app_label"]
        model_name = options["model_name"]

        model = apps.get_model(app_label=app_label, model_name=model_name)

        dfk_user_model = get_user_obj_perms_model(model)
        dfk_group_model = get_group_obj_perms_model(model)

        if dfk_user_model == UserObjectPermission:
            raise RuntimeError("DFK user permissions not active for model")

        if dfk_group_model == GroupObjectPermission:
            raise RuntimeError("DFK group permissions not active for model")

        content_type = ContentType.objects.get(
            app_label=app_label, model=model_name
        )

        self.migrate_user_permissions(
            dfk_user_model=dfk_user_model, content_type=content_type
        )
        self.migrate_group_permissions(
            dfk_group_model=dfk_group_model, content_type=content_type
        )

    def migrate_user_permissions(self, *, dfk_user_model, content_type):
        queryset = UserObjectPermission.objects.filter(
            content_type=content_type
        ).select_related("user", "permission")

        self.stdout.write(f"Migrating {queryset.count()} user permissions")

        migrated = 0
        removed = 0

        for perm in queryset.iterator():
            if (migrated + removed) % 1000 == 0:
                self.stdout.write(f"User permissions: {migrated=} {removed=}")

            if perm.content_object is None:
                perm.delete()
                removed += 1
            else:
                with transaction.atomic():
                    dfk_user_model.objects.create(
                        user=perm.user,
                        permission=perm.permission,
                        content_object=perm.content_object,
                    )
                    perm.delete()
                    migrated += 1

        self.stdout.write(f"Migrated {migrated} user permissions")
        self.stdout.write(f"Removed {removed} orphaned user permissions")

    def migrate_group_permissions(self, *, dfk_group_model, content_type):
        queryset = GroupObjectPermission.objects.filter(
            content_type=content_type
        ).select_related("group", "permission")

        self.stdout.write(f"Migrating {queryset.count()} group permissions")

        migrated = 0
        removed = 0

        for perm in queryset.iterator():
            if (migrated + removed) % 1000 == 0:
                self.stdout.write(f"Group permissions: {migrated=} {removed=}")

            if perm.content_object is None:
                perm.delete()
                removed += 1
            else:
                with transaction.atomic():
                    dfk_group_model.objects.create(
                        group=perm.group,
                        permission=perm.permission,
                        content_object=perm.content_object,
                    )
                    perm.delete()
                    migrated += 1

        self.stdout.write(f"Migrated {migrated} group permissions")
        self.stdout.write(f"Removed {removed} orphaned group permissions")
