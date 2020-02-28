from pathlib import Path

from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge, get_banner_path


class Command(BaseCommand):
    def handle(self, *args, **options):
        challenges = Challenge.objects.exclude(banner="")

        print(f"Found {len(challenges)} challenges with banners")

        for c in challenges:
            old_name = c.banner.name
            new_name = get_banner_path(c, Path(c.banner.name).name)

            if old_name == new_name:
                print(f"Skipping {old_name}")
            else:
                print(f"Migrating {old_name} to {new_name}")

                storage = c.banner.storage

                storage.copy(from_name=old_name, to_name=new_name)

                c.banner.name = new_name
                c.save()

                storage.delete(old_name)
