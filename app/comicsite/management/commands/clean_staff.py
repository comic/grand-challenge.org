from django.contrib.auth.models import User
from django.core.management import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    """
    Removes the staff bit from users who are not challenge admins or superusers
    """
    def handle(self, *args, **options):
        users = User.objects.filter(Q(is_staff=True),Q(is_superuser=False))
        for user in users:
            admin_groups = user.groups.filter(name__endswith='_admins')
            if len(admin_groups) == 0:
                print(f'Removing staff bit from {user.username}')
                user.is_staff = False
                user.save()
            else:
                print(f'{user.username} is admin for:')
                for group in admin_groups:
                    print(f'  - {group.admins_of_challenge.short_name}')

