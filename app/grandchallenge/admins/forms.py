from grandchallenge.groups.forms import UserGroupForm


class AdminsForm(UserGroupForm):
    role = "admin"
    user_complete_url = "admins:users-autocomplete"
