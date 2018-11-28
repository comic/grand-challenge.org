from django.contrib.auth.mixins import PermissionRequiredMixin
from django.conf import settings


class RetinaAPIPermissionMixin(PermissionRequiredMixin):
    raise_exception = True  # Raise 403 instead of useless 302 for api calls

    def has_permission(self):
        # TODO specific permissions?
        # uncomment next line and fix all tests accordingly to only allow users from retina_graders group
        # return self.request.user.groups.filter(name=settings.RETINA_GRADERS_GROUP_NAME).exists()
        return self.request.user.is_authenticated
