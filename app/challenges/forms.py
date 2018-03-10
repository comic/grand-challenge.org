from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from comicmodels.models import ComicSite


class ChallengeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ChallengeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('save', 'Save'))

    class Meta:
        model = ComicSite
        fields = ['short_name',
                  'description',
                  'require_participant_review',
                  'use_evaluation']
