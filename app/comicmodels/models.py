from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from guardian.shortcuts import assign_perm, remove_perm
from guardian.utils import get_anonymous_user

from challenges.models import ComicSite


class ComicSiteModel(models.Model):
    """
    An object which can be shown or used in the comicsite framework.
    This base class should handle common functions such as authorization.
    """
    title = models.SlugField(max_length=64, blank=False)
    challenge = models.ForeignKey(
        ComicSite, help_text="To which comicsite does this object belong?"
    )
    ALL = 'ALL'
    REGISTERED_ONLY = 'REG'
    ADMIN_ONLY = 'ADM'
    PERMISSIONS_CHOICES = (
        (ALL, 'All'),
        (REGISTERED_ONLY, 'Registered users only'),
        (ADMIN_ONLY, 'Administrators only'),
    )
    PERMISSION_WEIGHTS = ((ALL, 0), (REGISTERED_ONLY, 1), (ADMIN_ONLY, 2))
    permission_lvl = models.CharField(
        max_length=3, choices=PERMISSIONS_CHOICES, default=ALL
    )

    def __str__(self):
        """ string representation for this object"""
        return self.title

    def can_be_viewed_by(self, user):
        """ boolean, is user allowed to view this? """
        # check whether everyone is allowed to view this. Anymous user is the
        # only member of group 'everyone' for which permissions can be set
        anonymous_user = get_anonymous_user()
        if anonymous_user.has_perm("view_ComicSiteModel", self):
            return True

        else:
            # if not everyone has access,
            # check whether given user has permissions
            return user.has_perm("view_ComicSiteModel", self)

    def setpermissions(self, lvl):
        """ Give the right groups permissions to this object
            object needs to be saved before setting perms"""
        admingroup = self.challenge.admins_group
        participantsgroup = self.challenge.participants_group
        everyonegroup = Group.objects.get(name=settings.EVERYONE_GROUP_NAME)
        self.persist_if_needed()
        if lvl == self.ALL:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
            assign_perm("view_ComicSiteModel", everyonegroup, self)
        elif lvl == self.REGISTERED_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            assign_perm("view_ComicSiteModel", participantsgroup, self)
            remove_perm("view_ComicSiteModel", everyonegroup, self)
        elif lvl == self.ADMIN_ONLY:
            assign_perm("view_ComicSiteModel", admingroup, self)
            remove_perm("view_ComicSiteModel", participantsgroup, self)
            remove_perm("view_ComicSiteModel", everyonegroup, self)
        else:
            raise ValueError(
                f"Unknown permissions level '{lvl}'. "
                "I don't know which groups to give permissions to this object"
            )

    def persist_if_needed(self):
        """
        setting permissions needs a persisted object. This method makes sure.
        """
        if not self.id:
            super(ComicSiteModel, self).save()

    def save(self, *args, **kwargs):
        self.setpermissions(self.permission_lvl)
        super(ComicSiteModel, self).save()

    class Meta:
        abstract = True
        permissions = (("view_ComicSiteModel", "Can view Comic Site Model"),)


