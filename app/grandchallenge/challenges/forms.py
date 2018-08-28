from crispy_forms.bootstrap import TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, ButtonHolder
from django import forms
from django_select2.forms import Select2MultipleWidget

from grandchallenge.challenges.models import (
    Challenge,
    ExternalChallenge
)


class ChallengeCreateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('save', 'Save'))

    class Meta:
        model = Challenge
        fields = [
            'short_name',
            'description',
            'require_participant_review',
            'use_evaluation',
        ]


class ChallengeUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab('Information', 'title', 'description', ),
                Tab('Images', 'logo', 'banner', ),
                Tab(
                    'Metadata',
                    "task_types",
                    "modalities",
                    "structures",
                    'disclaimer',
                    'workshop_date',
                    'event_name',
                    'event_url',
                    'is_open_for_submissions',
                    'submission_page_name',
                    'number_of_submissions',
                    'last_submission_date',
                    'offers_data_download',
                    'number_of_downloads',
                    'publication_url',
                    'publication_journal_name',
                ),
                Tab(
                    'Registration',
                    'use_registration_page',
                    'require_participant_review',
                    'registration_page_text',
                ),
                Tab('Visibility', 'hidden', 'hide_signin', 'hide_footer'),
                Tab('Automated Evaluation', 'use_evaluation'),
            ),
            ButtonHolder(Submit('save', 'Save')),
        )

    class Meta:
        model = Challenge
        fields = [
            'title',
            'description',
            'logo',
            'banner',
            'disclaimer',
            'workshop_date',
            'event_name',
            'event_url',
            'is_open_for_submissions',
            'submission_page_name',
            'number_of_submissions',
            'last_submission_date',
            'offers_data_download',
            'number_of_downloads',
            'publication_url',
            'publication_journal_name',
            'use_registration_page',
            'require_participant_review',
            'registration_page_text',
            'hidden',
            'hide_signin',
            'hide_footer',
            'use_evaluation',
        ]
        widgets = {
            "workshop_date": forms.TextInput(attrs={'type': 'date'}),
            "last_submission_date": forms.TextInput(attrs={'type': 'date'}),
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
        }


information_items = (
    "short_name",
    "title",
    "homepage",
    "description",
    "task_types",
    "modalities",
    "structures",
    "logo",
    "hidden",
)
event_items = (
    'event_name',
    'event_url',
    'workshop_date',
)
data_items = (
    "data_license_agreement",
    "data_stored",
    "number_of_training_cases",
    "number_of_test_cases",
    "offers_data_download",
    "download_page",
    "number_of_downloads",
)
submission_items = (
    "is_open_for_submissions",
    "submission_page",
    "number_of_submissions",
    "last_submission_date",
)
publication_items = (
    "publication_url",
    "publication_journal_name",
)


class ExternalChallengeUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab('Information', *information_items, ),
                Tab('Event', *event_items, ),
                Tab('Data', *data_items, ),
                Tab('Submissions', *submission_items, ),
                Tab('Publication', *publication_items, ),
            ),
            ButtonHolder(Submit('save', 'Save')),
        )

    class Meta:
        model = ExternalChallenge
        fields = (
            *information_items,
            *event_items,
            *data_items,
            *submission_items,
            *publication_items,
        )
        widgets = {
            "workshop_date": forms.TextInput(attrs={'type': 'date'}),
            "last_submission_date": forms.TextInput(attrs={'type': 'date'}),
            "description": forms.Textarea,
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
        }
