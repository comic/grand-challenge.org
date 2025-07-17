from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.core.management import BaseCommand

from grandchallenge.discussion_forums.models import ForumTopic


class Command(BaseCommand):
    help = "Adds redirects for old forum pages"

    def handle(self, *args, **options):
        site = Site.objects.get_current()

        batch_size = 500
        redirects_to_add = []
        n_created = 0

        for topic in ForumTopic.objects.filter(source_object__isnull=False):
            redirects_to_add.append(
                Redirect(
                    site=site,
                    old_path=f"/forums/forum/{topic.source_object.forum.slug}-{topic.source_object.forum.pk}/topic/{topic.source_object.slug}-{topic.source_object.pk}/",
                    new_path=topic.get_absolute_url(),
                )
            )
            if len(redirects_to_add) >= batch_size:
                Redirect.objects.bulk_create(
                    redirects_to_add, ignore_conflicts=True
                )
                n_created += len(redirects_to_add)
                print(f"Created {n_created} new topic redirects")
                redirects_to_add = []

        if redirects_to_add:
            Redirect.objects.bulk_create(
                redirects_to_add, ignore_conflicts=True
            )
            n_created += len(redirects_to_add)
            print(f"Created {n_created} new topic redirects.")

        print("Finished adding redirects.")
