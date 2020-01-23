from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from comic.eyra.models import Benchmark, Algorithm


def set_algorithm_admin_group(
    algorithm: Algorithm
):
    admin_group = Group.objects.create(name=f"{algorithm.name} admin")
    admin_group.save()
    algorithm.admin_group = admin_group
    try:
        algorithm.creator.groups.add(admin_group)
    except AttributeError:
        # No creator set
        pass


def set_algorithm_default_permissions(
    algorithm: Algorithm
):
    assign_perm("change_algorithm", algorithm.admin_group, algorithm)
    assign_perm("change_group", algorithm.admin_group, algorithm.admin_group)


def set_benchmark_admin_group(
    benchmark: Benchmark
):
    admin_group = Group.objects.create(name=f"{benchmark.name} admin")
    admin_group.save()
    benchmark.admin_group = admin_group
    try:
        benchmark.creator.groups.add(admin_group)
    except AttributeError:
        # No creator set
        pass


def set_benchmark_default_permissions(
    benchmark: Benchmark
):
    assign_perm("change_benchmark", benchmark.admin_group, benchmark)
    assign_perm("change_group", benchmark.admin_group, benchmark.admin_group)
