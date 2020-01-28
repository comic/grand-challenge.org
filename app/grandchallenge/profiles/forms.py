import userena.forms as userena_forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.utils.translation import gettext_lazy as _
from django_countries import countries

from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.policies.models import Policy


class PreSocialForm(forms.Form):
    accept_terms = forms.BooleanField(
        label="I have read and agree to {}", required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("submit", "Submit"))
        accept_terms = self.fields["accept_terms"]
        accept_terms.label = accept_terms.label.format(
            oxford_comma(
                [
                    f'the <a href="{p.get_absolute_url()}">{p.title}</a>'
                    for p in Policy.objects.all()
                ]
            )
        )


class SignupFormExtra(userena_forms.SignupForm):
    first_name = forms.CharField(
        label=_("First Name"), max_length=30, required=True
    )
    last_name = forms.CharField(
        label=_("Last Name"), max_length=30, required=True
    )
    institution = forms.CharField(
        label=_("Institution"),
        max_length=100,
        required=True,
        help_text=_("Institution you are affiliated to."),
    )
    department = forms.CharField(
        label=_("Department"),
        max_length=100,
        required=True,
        help_text=_("Department you represent."),
    )
    country = forms.ChoiceField(
        label=_("Location"),
        choices=tuple([("00", _("-" * 9))] + list(countries)),
        required=True,
    )
    website = forms.URLField(
        label=_("Website"),
        max_length=150,
        required=False,
        help_text=_("A website which describes you or your department"),
    )
    accept_terms = forms.BooleanField(
        label="I have read and agree to {}.", required=True,
    )

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        accept_terms = self.fields["accept_terms"]
        accept_terms.label = accept_terms.label.format(
            oxford_comma(
                [
                    f'the <a href="{p.get_absolute_url()}">{p.title}</a>'
                    for p in Policy.objects.all()
                ]
            )
        )

    def clean_country(self):
        """Make sure the user changed the country field."""
        country = self.cleaned_data["country"]
        if country == "00":
            raise forms.ValidationError("Please choose a valid location.")

        return country

    def save(self):
        user = super().save()
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()

        user_profile = user.user_profile
        user_profile.institution = self.cleaned_data["institution"]
        user_profile.department = self.cleaned_data["department"]
        user_profile.country = self.cleaned_data["country"]
        user_profile.website = self.cleaned_data["website"]
        user_profile.save()

        return user


class EditProfileForm(userena_forms.EditProfileForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields["privacy"]
