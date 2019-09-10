from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm
from comic.eyra_algorithms.models import Algorithm


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
