from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand

from comicmodels.models import ComicSite


class Command(BaseCommand):
    def handle(self, *args, **options):
        challenges = ComicSite.objects.all()

        for challenge in challenges:

            if challenge.admins_group is None:
                try:
                    admins_group = Group.objects.get(name=challenge.admin_group_name())
                    print(f'Adding group {admins_group.name} to {challenge.short_name}')
                    challenge.admins_group = admins_group
                    challenge.save()
                except Group.DoesNotExist:
                    print(f'>>>> No admin group for {challenge.short_name}')

            if challenge.participants_group is None:
                try:
                    participants_group = Group.objects.get(name=challenge.participants_group_name())
                    print(f'Adding group {participants_group.name} to {challenge.short_name}')
                    challenge.participants_group = participants_group
                    challenge.save()
                except Group.DoesNotExist:
                    print(f'>>>> No participants group for {challenge.short_name}')

        print('----')

        groups = Group.objects.all()

        for group in groups:
            if 'admins' in group.name:
                try:
                    group.admins_of_challenge
                except ObjectDoesNotExist:
                    print(f'no challenge for {group.name}')

            if 'participants' in group.name:
                try:
                    group.participants_of_challenge
                except ObjectDoesNotExist:
                    print(f'no challenge for {group.name}')