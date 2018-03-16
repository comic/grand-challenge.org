import userena.forms as userena_forms
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from django_countries import countries


class SignupFormExtra(userena_forms.SignupForm):
    username = forms.RegexField(
        regex=r'^[a-zA-Z0-9]+$',
        max_length=30,
        widget=forms.TextInput(
            attrs=userena_forms.attrs_dict),
        label=_("Username"),
        error_messages={'invalid': _(
            'Username must contain only letters and numbers.')
        }
    )
    first_name = forms.CharField(
        label=_(u'First Name'),
        max_length=30,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z]+$',
                message=_(u"First name must only contain the characters a-z."),
            )
        ],
    )
    last_name = forms.CharField(
        label=_(u'Last Name'),
        max_length=30,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z-\s]+$',
                message=_(
                    u"Last name must only contain the characters a-z, spaces or hypens."),
            ),
        ],
    )
    institution = forms.CharField(
        label=_(u'Institution'),
        max_length=100,
        required=True,
        help_text=_(
            u'Institution you are affiliated to.'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z-\s]+$',
                message=_(
                    u"Institution must only contain the characters a-z, spaces or hypens."),
            ),
        ],
    )
    department = forms.CharField(
        label=_(u'Department'),
        max_length=100,
        required=True,
        help_text=_(u'Department you represent.'),
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z-\s]+$',
                message=_(
                    u"Department must only contain the characters a-z, spaces or hypens."),
            ),
        ],
    )
    country = forms.ChoiceField(label=_(u'Country'),
                                choices=tuple(
                                    [('00', _('-' * 9))] + list(countries)),
                                required=True)
    website = forms.URLField(
        label=_(u'Website'),
        max_length=150,
        required=False,
        help_text=_(
            u'A website which describes you or your department')
    )

    def __init__(self, *args, **kw):
        super(SignupFormExtra, self).__init__(*args, **kw)

    def clean_country(self):
        """ Make sure the user changed the country field.
        """
        country = self.cleaned_data['country']
        if country == '00':
            raise forms.ValidationError("Please choose a valid country.")
        return country

    def save(self):
        user = super(SignupFormExtra, self).save()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        user_profile = user.user_profile
        user_profile.institution = self.cleaned_data['institution']
        user_profile.department = self.cleaned_data['department']
        user_profile.country = self.cleaned_data['country']
        user_profile.save()

        return user


class EditProfileForm(userena_forms.EditProfileForm):
    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        del self.fields['privacy']
