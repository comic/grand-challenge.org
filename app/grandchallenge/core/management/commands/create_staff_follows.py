from actstream.actions import follow, is_following
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        total_follows = 0
        staff = list(get_user_model().objects.filter(is_staff=True).all())

        for user in staff:
            for site in Site.objects.all():
                if not is_following(user=user, obj=site):
                    follow(
                        user=user,
                        obj=site,
                        actor_only=False,
                        send_action=False,
                    )
                    self.stdout.write(
                        f"Created follow: {str(user.username)} --> {str(site.name)}"
                    )
                    total_follows += 1

        if total_follows == 0:
            self.stdout.write(self.style.WARNING("No new follows created."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done! Created {total_follows} follows.")
            )
