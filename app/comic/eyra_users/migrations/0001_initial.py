from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import migrations
from guardian.shortcuts import assign_perm


def create_default_group(apps, schema_editor):
    default_group, created = Group.objects.get_or_create(
        name="default"
    )
    default_group.save()
    assign_perm('eyra_benchmarks.add_benchmark', default_group)
    assign_perm('eyra_benchmarks.add_submission', default_group)
    assign_perm('eyra_algorithms.add_algorithm', default_group)
    assign_perm('eyra_algorithms.add_implementation', default_group)


def assign_anon_permissions(apps, schema_editor):
    # guardian anon user
    anon_user = User.get_anonymous()
    assign_perm('eyra_benchmarks.view_benchmark', anon_user)
    assign_perm('eyra_benchmarks.view_submission', anon_user)
    assign_perm('eyra_algorithms.view_algorithm', anon_user)
    assign_perm('eyra_algorithms.view_implementation', anon_user)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('guardian', '0001_initial'),
        ('eyra_benchmarks', '0001_initial'),
        ('eyra_data', '0001_initial'),
        ('eyra_algorithms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_group, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(assign_anon_permissions, reverse_code=migrations.RunPython.noop),
    ]
