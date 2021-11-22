import re

from django.core.management import BaseCommand

from grandchallenge.profiles.models import UserProfile


class Command(BaseCommand):
    def handle(self, *args, **options):
        users_with_website = UserProfile.objects.exclude(website="")
        count = 0
        for user in users_with_website:
            if user.website and not user.website.startswith("https://"):
                user.website = "https://" + re.sub(
                    r"http://", "", user.website
                )
                count += 1
        UserProfile.objects.bulk_update(users_with_website, ["website"])
        print(f"Updated {count} user profiles")
