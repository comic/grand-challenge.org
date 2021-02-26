import logging

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    users = None

    def handle(self, *args, **options):
        """
        Idempotent command that creates a superuser and adds a token for
        retina_import_user.
        """
        if not settings.DEBUG:
            raise RuntimeError(
                "Skipping this command, server is not in DEBUG mode."
            )

        # Create superuser
        if not get_user_model().objects.filter(username="su").exists():
            su = get_user_model().objects.create_superuser(
                "su", "su@example.com", "su"
            )
            EmailAddress.objects.create(
                user=su, email=su.email, verified=True, primary=True,
            )

        # Create default token for retina_import_user
        Token.objects.get_or_create(
            user=get_user_model().objects.get(
                username=settings.RETINA_IMPORT_USER_NAME
            ),
            key="e8db90bfbea3c35f40b4537fdca9b3bf1cd78a51",
        )
