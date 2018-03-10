from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    """
    Removes the staff bit from users who are not superusers
    """

    def handle(self, *args, **options):
        users = User.objects.filter(Q(is_staff=True), Q(is_superuser=False))
        for user in users:
            print(f'Removing staff bit from {user.username}')
            user.is_staff = False
            user.save()
