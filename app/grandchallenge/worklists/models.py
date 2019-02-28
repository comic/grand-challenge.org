from django.contrib.auth.models import User
from django.db import models
from django.db.models import CharField
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image


class WorklistSet(UUIDModel):
    """
    Represents a collection of worklists for a single user.
    """

    title = CharField(null=False, blank=False, max_length=255)
    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)

    def get_children(self):
        return Worklist.objects.filter(set=self.pk)

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))

    class Meta(UUIDModel.Meta):
        unique_together = ("title", "user")


class Worklist(UUIDModel):
    """
    Represents a collection of images.
    """

    title = CharField(null=False, blank=False, max_length=255)
    set = models.ForeignKey(WorklistSet, null=False, on_delete=models.CASCADE)
    images = models.ManyToManyField(to=Image, related_name="worklist", null=True)

    def __str__(self):
        return "%s (%s)" % (self.title, str(self.id))

    class Meta(UUIDModel.Meta):
        unique_together = ("title", "set")
