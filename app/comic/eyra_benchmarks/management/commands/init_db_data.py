from django.contrib.auth.models import Group, User
from django.core.management import BaseCommand
from guardian.shortcuts import assign_perm

from comic.eyra_data.models import DataType


def create_default_group():
    default_group, created = Group.objects.get_or_create(
        name="default"
    )
    default_group.save()
    assign_perm('eyra_benchmarks.add_benchmark', default_group)
    assign_perm('eyra_benchmarks.add_submission', default_group)
    assign_perm('eyra_algorithms.add_algorithm', default_group)
    assign_perm('eyra_algorithms.add_implementation', default_group)


def assign_anon_permissions():
    # guardian anon user
    anon_user = User.get_anonymous()
    assign_perm('eyra_benchmarks.view_benchmark', anon_user)
    assign_perm('eyra_benchmarks.view_submission', anon_user)
    assign_perm('eyra_algorithms.view_algorithm', anon_user)
    assign_perm('eyra_algorithms.view_implementation', anon_user)


class Command(BaseCommand):
    def handle(self, *args, **options):
        create_default_group()
        assign_anon_permissions()

        output_metrics_type, created = DataType.objects.get_or_create(
            name='OutputMetrics',
            description='Metrics (.json)'
        )
        output_metrics_type.save()

