from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import ValidationError
from django.forms import CheckboxInput, Select
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from grandchallenge.core.forms import SaveFormInitMixin
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
            "notification_email_choice",
            "receive_newsletter",
        )
        widgets = {"receive_newsletter": CheckboxInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk is None:
            self.fields.pop("mugshot")
            self.fields.pop("display_organizations")
        else:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

        self.fields["country"].label = "Location"
        self.fields["receive_newsletter"].initial = True

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        instance.user.first_name = self.cleaned_data["first_name"]
        instance.user.last_name = self.cleaned_data["last_name"]
        instance.user.save()

        return instance

    def clean_website(self):
        url = self.cleaned_data["website"]

        if url and not url.startswith("https://"):
            raise ValidationError("Your url needs to start with https://")

        return url

    def clean(self):
        first_name = self.cleaned_data.get("first_name", "")
        last_name = self.cleaned_data.get("last_name", "")

        c = slice(-2, None)
        if first_name[c] == first_name[c].upper() == last_name[c]:
            # Hack around a scripts creating
            # accounts with names fooAB barAB etc.
            raise ValidationError("Account details invalid")


class SignupForm(UserProfileForm):
    accept_terms = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # mark_safe ok here as we control the policy page titles
        self.fields["accept_terms"].label = mark_safe(
            "I have read and agree to {}.".format(
                oxford_comma(
                    [
                        f"the <a href={p.get_absolute_url()!r}>{p.title}</a>"
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
        user_profile.receive_newsletter = self.cleaned_data[
            "receive_newsletter"
        ]
        user_profile.save()


class NewsletterSignupForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("receive_newsletter",)
        widgets = {
            "receive_newsletter": Select(
                choices=((True, "Yes, sign me up!"), (False, "No, thanks."))
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["receive_newsletter"].help_text = None
        self.helper.form_show_labels = False


class SubscriptionPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            "notification_email_choice",
            "receive_newsletter",
        )
        widgets = {
            "receive_newsletter": CheckboxInput,
        }

    def __init__(
        self,
        *args,
        notification_email_choice,
        receive_newsletter,
        autosubmit,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.initial["notification_email_choice"] = notification_email_choice
        self.initial["receive_newsletter"] = receive_newsletter

        self.helper = FormHelper(self)
        self.helper.form_id = "unsubscribeForm"

        if autosubmit:
            self.helper.form_class = "auto-submit"
            self.fields["notification_email_choice"].disabled = True
            self.fields["receive_newsletter"].disabled = True
        else:
            self.helper.add_input(Submit("save", "save"))
