from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from grandchallenge.archives.models import Archive


class Command(BaseCommand):
    """
    Sets correct object level permissions for retina archives.
    Adds users in retina_grader group as users and admins in retina_admin
    group as editors.
    """

    help = "Sets correct object level permissions for retina archives"

    def handle(self, *args, **options):
        users = Group.objects.get(
            name=settings.RETINA_GRADERS_GROUP_NAME
        ).user_set.all()
        editors = Group.objects.get(
            name=settings.RETINA_ADMINS_GROUP_NAME
        ).user_set.all()
        archives = Archive.objects.filter(
            title__in=[
                "AREDS - GA selection",
                "kappadata",
                "Rotterdam_Study_1",
                "Rotterdam Study 1",
                "Australia",
                "RS1",
                "RS2",
                "RS3",
            ]
        )
        for archive in archives:
            self.stdout.write(
                f"Creating groups and permissions for archive: {archive.title}"
            )
            try:
                archive.create_groups()
            except IntegrityError as e:
                if (
                    'duplicate key value violates unique constraint "auth_group_name_key"'
                    in str(e)
                ):
                    self.stdout.write(
                        self.style.WARNING(
                            f"Permission groups already exist for {archive.title}"
                        )
                    )
                else:
                    raise
            archive.save()
            for user in users:
                self.stdout.write(
                    f"Adding {user.username} as user for archive: {archive.title}"
                )
                archive.add_user(user)
            for editor in editors:
                self.stdout.write(
                    f"Adding {editor.username} as editor for archive: {archive.title}"
                )
                archive.add_editor(editor)
