from itertools import chain

from actstream.actions import follow, is_following
from django.core.management import BaseCommand

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
from grandchallenge.reader_studies.models import ReaderStudy


class Command(BaseCommand):
    def handle(self, *args, **options):
        total_follows = 0
        model_instances = list(
            chain(
                Algorithm.objects.all(),
                Archive.objects.all(),
                ReaderStudy.objects.all(),
            )
        )

        for instance in model_instances:
            for user in instance.editors_group.user_set.all():
                if not is_following(user=user, obj=instance):
                    follow(
                        user=user,
                        obj=instance,
                        actor_only=False,
                        send_action=False,
                    )
                    self.stdout.write(
                        f"Created {instance._meta.model_name} follow: {str(user.username)} --> {str(instance.title)}"
                    )
                    total_follows += 1

        if total_follows == 0:
            self.stdout.write(self.style.WARNING("No new follows created."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Done! Created {total_follows} follows.")
            )
