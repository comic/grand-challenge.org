from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.subdomains.utils import reverse_lazy


class ChallengeCreateForm(forms.ModelForm):
    def __init__(self, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
        self.fields["contact_email"].required = True
        self.fields["contact_email"].initial = creator.email

    class Meta:
        model = Challenge
        fields = [
            "short_name",
            "description",
            "require_participant_review",
            "use_evaluation",
            "contact_email",
        ]


common_information_items = (
    "title",
    "description",
    "task_types",
    "modalities",
    "structures",
    "organizations",
    "series",
    "publications",
    "hidden",
    "educational",
)

common_images_items = ("logo", "social_image")

event_items = ("event_url", "workshop_date")

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
                Tab(
                    "Information",
                    *common_information_items,
                    "display_forum_link",
                    "disclaimer",
                    "contact_email",
                ),
                Tab("Images", "banner", *common_images_items),
                Tab("Event", *event_items),
                Tab("Registration", *registration_items),
                Tab("Automated Evaluation", "use_evaluation", "use_teams"),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    class Meta:
        model = Challenge
        fields = [
            *common_information_items,
            "display_forum_link",
            "disclaimer",
            "contact_email",
            "banner",
            *common_images_items,
            *event_items,
            *registration_items,
            "use_evaluation",
            "use_teams",
        ]
        widgets = {
            "workshop_date": forms.TextInput(attrs={"type": "date"}),
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "series": Select2MultipleWidget,
            "publications": Select2MultipleWidget,
            "registration_page_text": SummernoteInplaceWidget(),
        }
        help_texts = {
            "publications": format_lazy(
                (
                    "The publications associated with this archive. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            )
        }

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data["hidden"] and not cleaned_data.get("logo"):
            raise ValidationError("A logo is required for public challenges")

        if not cleaned_data["hidden"] and not cleaned_data.get(
            "contact_email"
        ):
            raise ValidationError("A contact email is required")

        return cleaned_data


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
        )
        widgets = {
            "workshop_date": forms.TextInput(attrs={"type": "date"}),
            "description": forms.Textarea,
            "task_types": Select2MultipleWidget,
            "modalities": Select2MultipleWidget,
            "structures": Select2MultipleWidget,
            "organizations": Select2MultipleWidget,
            "series": Select2MultipleWidget,
            "publications": Select2MultipleWidget,
        }
        help_texts = {
            "publications": format_lazy(
                (
                    "The publications associated with this archive. "
                    'If your publication is missing click <a href="{}">here</a> to add it '
                    "and then refresh this page."
                ),
                reverse_lazy("publications:create"),
            )
        }
