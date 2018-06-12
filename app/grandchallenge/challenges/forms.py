from crispy_forms.bootstrap import TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, ButtonHolder
from django import forms

from grandchallenge.challenges.models import Challenge


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
                Tab('Information', 'title', 'description', 'logo_path'),
                Tab('Layout', 'header_image', 'skin', 'disclaimer'),
                Tab(
                    'Metadata',
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
                    'Users',
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
            'logo_path',
            'header_image',
            'skin',
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
