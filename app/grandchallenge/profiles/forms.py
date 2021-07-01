from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.policies.models import Policy
from grandchallenge.profiles.models import UserProfile


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label=_("First Name"), max_length=30, required=True
    )
    last_name = forms.CharField(
        label=_("Last Name"), max_length=30, required=True
    )

    class Meta:
        model = UserProfile
        fields = (
            "first_name",
            "last_name",
            "mugshot",
            "institution",
            "department",
            "country",
            "website",
            "display_organizations",
            "receive_notification_emails",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk is None:
            self.fields.pop("mugshot")
            self.fields.pop("display_organizations")
        else:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

        self.fields["country"].label = "Location"

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        instance.user.first_name = self.cleaned_data["first_name"]
        instance.user.last_name = self.cleaned_data["last_name"]
        instance.user.save()

        return instance


class SignupForm(UserProfileForm):
    accept_terms = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # mark_safe ok here as we control the policy page titles
        self.fields["accept_terms"].label = mark_safe(
            "I have read and agree to {}.".format(
                oxford_comma(
                    [
                        f'the <a href="{p.get_absolute_url()}">{p.title}</a>'
                        for p in Policy.objects.all()
                    ]
                )
            )
        )

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()

        user_profile = user.user_profile
        user_profile.institution = self.cleaned_data["institution"]
        user_profile.department = self.cleaned_data["department"]
        user_profile.country = self.cleaned_data["country"]
        user_profile.website = self.cleaned_data["website"]
        user_profile.save()
