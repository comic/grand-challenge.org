import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    users = None

    def handle(self, *args, **options):
        """
        Idempotent command that adds retina user to all existing archives and
        algorithms.
        """
        if not settings.DEBUG:
            raise RuntimeError(
                "Skipping this command, server is not in DEBUG mode."
            )

        # Add retina user to imported archives and algorithms
        retina_user = get_user_model().objects.get(username="retina")
        for model in (Archive, Algorithm):
            for obj in model.objects.all():
                obj.add_user(retina_user)
