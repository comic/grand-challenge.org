from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from django import forms
from django_select2.forms import Select2MultipleWidget
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.challenges.models import Challenge, ExternalChallenge


class ChallengeCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))

    class Meta:
        model = Challenge
        fields = [
            "short_name",
            "description",
            "require_participant_review",
            "use_evaluation",
        ]


common_information_items = (
    "title",
    "description",
    "task_types",
    "modalities",
    "structures",
    "series",
    "hidden",
    "educational",
)

common_images_items = ("logo",)

event_items = ("event_url", "workshop_date")

publication_items = (
    "publication_url",
    "publication_journal_name",
    "publication_citation_count",
    "publication_google_scholar_id",
)
registration_items = (
    "use_registration_page",
    "require_participant_review",
    "registration_page_text",
)


class ChallengeUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab("Information", *common_information_items, "disclaimer"),
                Tab("Images", "banner", *common_images_items),
                Tab("Event", *event_items),
                Tab("Registration", *registration_items),
                Tab("Automated Evaluation", "use_evaluation"),
                Tab("Publication", *publication_items),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    class Meta:
        model = Challenge
        fields = [
            *common_information_items,
            "disclaimer",
            "banner",
            *common_images_items,
            *event_items,
            *registration_items,
            "use_evaluation",
            *publication_items,
        ]
        widgets = {
            "workshop_date": forms.TextInput(attrs={"type": "date"}),
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "series": Select2MultipleWidget,
            "registration_page_text": SummernoteInplaceWidget(),
        }


data_items = (
    "data_license_agreement",
    "data_stored",
    "number_of_training_cases",
    "number_of_test_cases",
)


class ExternalChallengeUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    "Information",
                    "short_name",
                    "homepage",
                    *common_information_items,
                ),
                Tab("Images", *common_images_items),
                Tab("Event", *event_items),
                Tab("Data", *data_items),
                Tab("Publication", *publication_items),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    class Meta:
        model = ExternalChallenge
        fields = (
            "short_name",
            "homepage",
            *common_information_items,
            *common_images_items,
            *event_items,
            *data_items,
            *publication_items,
        )
        widgets = {
            "workshop_date": forms.TextInput(attrs={"type": "date"}),
            "description": forms.Textarea,
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "series": Select2MultipleWidget,
        }
