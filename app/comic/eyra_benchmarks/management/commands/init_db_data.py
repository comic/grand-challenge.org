from django.core.management import BaseCommand

from comic.eyra_data.models import DataType


class Command(BaseCommand):
    def handle(self, *args, **options):
        from guardian.shortcuts import assign_perm
        from django.contrib.auth.models import Group

        group, created = Group.objects.get_or_create(
            name="default"
        )
        group.save()

        assign_perm('eyra_benchmarks.add_benchmark', group)
        assign_perm('eyra_benchmarks.change_benchmark', group)

        output_metrics_type = DataType(
            name='OutputMetrics',
            description='Metrics (.json)'
        )
        output_metrics_type.save()

