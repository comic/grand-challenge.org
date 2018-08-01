from crispy_forms.bootstrap import TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, ButtonHolder
from django import forms

from grandchallenge.challenges.models import Challenge, ExternalChallenge


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


class ExternalChallengeUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'Information',
                    'title',
                    'homepage',
                    'description',
                    'logo',
                    'hidden',
                ),
                Tab(
                    'Event',
                    'event_name',
                    'event_url',
                    'workshop_date',
                ),
                Tab(
                    'Data',
                    "offers_data_download",
                    "download_page",
                    "number_of_downloads",
                ),
                Tab(
                    'Submissions',
                    "is_open_for_submissions",
                    "submission_page",
                    "number_of_submissions",
                    "last_submission_date",
                ),
                Tab(
                    'Publication',
                    "publication_url",
                    "publication_journal_name",
                ),
            ),
            ButtonHolder(Submit('save', 'Save')),
        )

    class Meta:
        model = ExternalChallenge
        fields = (
            # Information
            "title",
            "homepage",
            "description",
            "logo",
            "hidden",

            # Event
            "event_name",
            "event_url",
            "workshop_date",

            # Data
            "offers_data_download",
            "download_page",
            "number_of_downloads",

            # Submissions
            "is_open_for_submissions",
            "submission_page",
            "number_of_submissions",
            "last_submission_date",

            # Publication
            "publication_url",
            "publication_journal_name",
        )
        widgets = {
            "workshop_date": forms.TextInput(attrs={'type': 'date'}),
            "last_submission_date": forms.TextInput(attrs={'type': 'date'}),
        }
