from django.contrib.auth.models import User
from django.db import models
from django.db.models import CharField
from guardian.shortcuts import assign_perm
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image


class WorklistSet(UUIDModel):
    """
    Represents a collection of worklists for a single user.
    """

    title = CharField(max_length=255)
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)

    def get_children(self):
        return Worklist.objects.filter(set=self.pk)

    def save(self, *args, **kwargs):
        created = self._state.adding
        super(WorklistSet, self).save(*args, **kwargs)

        if created and self.user is not None:
            assign_perm("view_worklistset", self.user, self)

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))


class Worklist(UUIDModel):
    """
    Represents a collection of images.
    """

    title = CharField(max_length=255)
    set = models.ForeignKey(WorklistSet, null=False, on_delete=models.CASCADE)
    images = models.ManyToManyField(
        to=Image, related_name="worklist", blank=True
    )

    def save(self, *args, **kwargs):
        created = self._state.adding
        super(Worklist, self).save(*args, **kwargs)

        set = WorklistSet.objects.get(pk=self.set)
        if created and set.user is not None:
            assign_perm("view_worklist", set.user, self)
            assign_perm("change_worklist", set.user, self)
            assign_perm("delete_worklist", set.user, self)

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))

    class Meta(UUIDModel.Meta):
        unique_together = ("title", "set")
