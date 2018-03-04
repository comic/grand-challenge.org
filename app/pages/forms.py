from crispy_forms.helper import FormHelper
from django import forms
from django.db.models import BLANK_CHOICE_DASH

from comicmodels.models import Page


class PageCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        challenge_name = kwargs.pop('challenge_short_name', None)

        super(PageCreateForm, self).__init__(*args, **kwargs)

        if challenge_name is not None and 'html' in self.fields:
            self.fields['html'].widget.config['comicsite'] = challenge_name

        self.helper = FormHelper(self)

    class Meta:
        model = Page
        fields = ('title', 'permission_lvl', 'display_title', 'hidden', 'html')


class PageUpdateForm(PageCreateForm):
    """ Like the page update form but you can also move the page """
    move = forms.CharField(widget=forms.Select)
    move.required = False
    move.widget.choices = (
        (BLANK_CHOICE_DASH[0]),
        (Page.FIRST, 'First'),
        (Page.UP, 'Up'),
        (Page.DOWN, 'Down'),
        (Page.LAST, 'Last'),
    )
