from rest_framework_guardian import filters


class UserProfileObjectPermissionsFilter(filters.ObjectPermissionsFilter):
    perm_format = "%(app_label)s.view_profile"
