from django import forms
from django.utils.translation import ugettext_lazy as _
from django_countries.countries import COUNTRIES

from userena.forms import SignupForm

class SignupFormExtra(SignupForm):
    institution = forms.CharField(label=_(u'Institution'),
            max_length = 100,
            required = True,
            help_text=_(u'Institution you are affiliated to.'))
    department = forms.CharField(label=_(u'Department'),
            max_length = 100,
            required = True,
            help_text=_(u'Department you represent.'))
    country = forms.ChoiceField(label=_(u'Country'),
            choices=COUNTRIES,
            required = True)
    website = forms.CharField(label=_(u'Website'),
            max_length = 150,
            required = False)
    first_name = forms.CharField(label=_(u'First Name'),
            max_length = 30,
            required = True)
    last_name = forms.CharField(label=_(u'Last Name'),
            max_length = 30,
            required = True)

    def __init__(self, *args, **kw):
        """ Bit of hackery to get the first and last name at the top of the form.
        """
        super(SignupFormExtra,self).__init__(*args,**kw)
        # Put the first and last name at the top.
        new_order = self.fields.keyOrder[:-2]
        new_order.insert(0, 'first_name')
        new_order.insert(1, 'last_name')
        self.fields.keyOrder = new_order

    def save(self):
        user = super(SignupFormExtra,self).save()
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        user_profile = user.get_profile()
        user_profile.institution = self.cleaned_data['institution']
        user_profile.department = self.cleaned_data['department']
        user_profile.save()

        return user
