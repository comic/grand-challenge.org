from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.blogs.models import Post


@receiver(m2m_changed, sender=Post.authors.through)
def update_permissions_on_authors_changed(
    instance, action, reverse, pk_set, **_
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        users = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            posts = instance.blog_authors.all()
        else:
            posts = Post.objects.filter(pk__in=pk_set)
    else:
        posts = Post.objects.get(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            users = instance.authors.all()
        else:
            users = get_user_model().objects.filter(pk__in=pk_set)

    op = assign_perm if "add" in action else remove_perm

    for user in users:
        op("change_post", user, posts)
