from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            print(f'{user.username} - {user.email}')
