from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class GroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = []

    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("users", False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["users"].initial = self.instance.user_set.all()

    def save_m2m(self):
        self.instance.user_set.set(self.cleaned_data["users"])

    def save(self, *args, **kwargs):
        instance = super().save()
        # Save many-to-many data
        self.save_m2m()
        return instance


# Create a new Group admin.
class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ["permissions"]
    search_fields = ("name",)
    ordering = ("name",)


# Unregister the original Group admin.
admin.site.unregister(Group)
# Register the new Group ModelAdmin.
admin.site.register(Group, GroupAdmin)
