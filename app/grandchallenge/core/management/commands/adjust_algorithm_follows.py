from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from grandchallenge.algorithms.models import Algorithm


class Command(BaseCommand):
    def handle(self, *args, **options):
        updated_follows = 0
        for algorithm in Algorithm.objects.all():
            for admin in algorithm.editors_group.user_set.all():
                f = Follow.objects.filter(
                    user=admin,
                    object_id=algorithm.pk,
                    content_type=ContentType.objects.filter(
                        model="algorithm"
                    ).get(),
                    flag="",
                ).get()
                f.flag = "access_request"
                f.save()
                if f:
                    updated_follows += 1

        print(f"{updated_follows} follows updated.")
