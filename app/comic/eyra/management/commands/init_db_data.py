from django.contrib.auth.models import Group, User
from django.core.management import BaseCommand
from guardian.shortcuts import assign_perm


def create_default_group():
    default_group, created = Group.objects.get_or_create(
        name="default"
    )
    default_group.save()
    assign_perm('eyra.add_benchmark', default_group)
    assign_perm('eyra.add_submission', default_group)
    assign_perm('eyra.add_algorithm', default_group)


def assign_anon_permissions():
    # guardian anon user
    anon_user = User.get_anonymous()
    assign_perm('eyra.view_benchmark', anon_user)
    assign_perm('eyra.view_submission', anon_user)
    assign_perm('eyra.view_algorithm', anon_user)


class Command(BaseCommand):
    def handle(self, *args, **options):
        create_default_group()
        assign_anon_permissions()

