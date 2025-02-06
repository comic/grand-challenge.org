from grandchallenge.groups.forms import UserGroupForm


class AdminsForm(UserGroupForm):
    role = "admin"
    url = "admins:users-autocomplete"
