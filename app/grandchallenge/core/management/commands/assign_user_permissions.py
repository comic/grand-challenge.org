from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from guardian.shortcuts import assign_perm
from guardian.utils import get_anonymous_user


class Command(BaseCommand):
    def handle(self, *args, **options):
        num = 0
        for user in get_user_model().objects.all():
            if user != get_anonymous_user() and not user.has_perm(
                "view_userprofile", user.user_profile
            ):
                assign_perm("view_userprofile", user, user.user_profile)
                num += 1
        print("Assigned 'view_userprofile' permission to", num, "users.")
