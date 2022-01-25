from django.core.management import BaseCommand
from guardian.shortcuts import assign_perm

from grandchallenge.archives.models import Archive


class Command(BaseCommand):
    def handle(self, *args, **options):
        for archive in Archive.objects.all():
            editors_group = archive.editors_group
            uploaders_group = archive.uploaders_group
            users_group = archive.users_group
            items = archive.items.all()
            assign_perm("view_archiveitem", editors_group, items)
            assign_perm("view_archiveitem", uploaders_group, items)
            assign_perm("view_archiveitem", users_group, items)
            assign_perm("change_archiveitem", editors_group, items)
            assign_perm("change_archiveitem", editors_group, items)
