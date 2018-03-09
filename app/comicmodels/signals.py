from importlib import reload

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.urlresolvers import clear_url_caches
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from comicmodels.models import ComicSite
from evaluation.models import Config


def reload_url_conf():
    """
    urlpatterns for project admin in urls.py are generated based on the current
    projects in the database. When a project gets added, the admin urls for the
    new project are not in the imported urls.py. A reload is required
    """
    import comicsite.urls
    import comic.urls
    reload(comicsite.urls)
    reload(comic.urls)


def add_standard_permissions(group, objname):
    can_add_obj = Permission.objects.get(codename="add_" + objname)
    can_change_obj = Permission.objects.get(codename="change_" + objname)
    can_delete_obj = Permission.objects.get(codename="delete_" + objname)
    group.permissions.add(can_add_obj, can_change_obj, can_delete_obj)


@receiver(post_save, sender=ComicSite)
def setup_challenge_groups(sender: ComicSite, instance: ComicSite = None,
                           created: bool = False, **kwargs):
    reload_url_conf()
    clear_url_caches()

    if created:
        # Create the evaluation config
        Config.objects.create(challenge=instance)

        # Create the groups only on first save
        admins_group = Group.objects.create(name=instance.admin_group_name())
        participants_group = Group.objects.create(
            name=instance.participants_group_name())

        instance.admins_group = admins_group
        instance.participants_group = participants_group
        instance.save()

        assign_perm("change_comicsite", admins_group, instance)

        # add all permissions for pages and comicsites so
        # these can be edited by admin group
        add_standard_permissions(admins_group, "comicsite")
        add_standard_permissions(admins_group, "page")

        # add current user to admins for this site
        try:
            instance.creator.groups.add(admins_group)

            # Add the creator to the staff
            instance.creator.is_staff = True
            instance.creator.save()
        except AttributeError:
            # No creator set
            pass


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_everyone_user_group(sender: settings.AUTH_USER_MODEL,
                               instance: settings.AUTH_USER_MODEL = None,
                               created: bool = False, **kwargs):
    # Create the everyone usergroup when the anonymoususer is created
    if created and instance.username == settings.ANONYMOUS_USER_NAME:
        group, _ = Group.objects.get_or_create(
            name=settings.EVERYONE_GROUP_NAME)
        instance.groups.add(group)
