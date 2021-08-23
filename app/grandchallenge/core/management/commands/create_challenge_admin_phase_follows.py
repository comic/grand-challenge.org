from actstream.actions import follow, is_following
from django.core.management import BaseCommand

from grandchallenge.challenges.models import Challenge


class Command(BaseCommand):
    def handle(self, *args, **options):
        total_follows = 0

        for challenge in Challenge.objects.all():
            for phase in challenge.phase_set.all():
                for admin in challenge.get_admins():
                    if not is_following(user=admin, obj=phase):
                        follow(
                            user=admin,
                            obj=phase,
                            actor_only=False,
                            send_action=False,
                        )
                    self.stdout.write(
                        f"Created follow: {str(admin.username)} --> {str(phase.title)}"
                    )
                    total_follows += 1
        if total_follows == 0:
            self.stdout.write(self.style.WARNING("No new follows created."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done! Created {total_follows} follows.")
            )
