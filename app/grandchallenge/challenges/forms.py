from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    ButtonHolder,
    Div,
    Fieldset,
    HTML,
    Layout,
    Submit,
)
from django import forms
from django.core.exceptions import ValidationError
from django.forms import Select
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    ExternalChallenge,
)
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
            "access_request_handling",
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
    "access_request_handling",
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
                Tab("Teams", "use_teams"),
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


general_information_items = (
    "title",
    "challenge_short_name",
    "contact_email",
    "abstract",
    "start_date",
    "end_date",
    "organizers",
    "affiliated_event",
    "task_types",
    "structures",
    "modalities",
    "challenge_type",
    "challenge_setup",
    "data_set",
    "submission_assessment",
    "challenge_publication",
    "code_availability",
    "expected_number_of_teams",
)
phase_1_items = (
    "phase_1_number_of_submissions_per_team",
    "phase_1_number_of_test_images",
)
phase_2_items = (
    "phase_2_number_of_submissions_per_team",
    "phase_2_number_of_test_images",
)


class ChallengeRequestForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = (
            *general_information_items,
            "number_of_tasks",
            "average_size_of_test_image",
            "inference_time_limit",
            *phase_1_items,
            *phase_2_items,
        )
        widgets = {
            "start_date": forms.TextInput(attrs={"type": "date"}),
            "end_date": forms.TextInput(attrs={"type": "date"}),
            "challenge_type": forms.Select(
                attrs={"onchange": "updateForm();"}
            ),
        }
        help_texts = {
            "challenge_type": "What type is this challenge? "
            "Type I : predictions submission - test data are open, "
            "participants run their algorithms locally and submit "
            "their predictions which are evaluated against a secret "
            "ground truth on the platform<br>"
            "Type II: docker container submission – test data are "
            "secret, participants submit algorithms as docker "
            "containers, which are run on the secret test set on "
            "our servers and then evaluated against a secret ground "
            "truth. <br>"
            "We encourage Type II challenges whenever possible. <br>"
            "For more information see our documentation.",
            "code_availability": "Will the participants’ code be accessible after "
            "the challenge? <br>For Type I challenges, you could "
            "ask participants to submit a Github link to their "
            "algorithm along with their submission. <br>For Type "
            "II challenges, algorithms will be stored on "
            "Grand Challenge and we encourage organizers to "
            "incentivize an open source policy, for example "
            "in the form of a linked Github repo with an "
            "appropriate license.",
            "data_set": "Describe the training and test datasets you are planning to "
            "use. <br>For Type I challenges, think about where you will "
            "store the data (read about the option here).<br>For Type "
            "II challenges, the test dataset will need to be uploaded "
            "to Grand Challenge (read more about that here).",
        }

    def __init__(self, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.creator = creator
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        "<br><p>Thank you for considering to host your challenge"
                        " on our platform! <br><br>To find out if Grand Challenge is "
                        "a suitable platform for you, please tell us "
                        "more about your planned challenge.<br>"
                        "The answers you provide below will help our team of "
                        "reviewers decide whether or not and in "
                        "what way we can support your challenge.<br><br>"
                        "To learn more about how challenges work on Grand "
                        "Challenge, take a look at our documentation. Read more "
                        "about the challenge request procedure here.</p><br>"
                    ),
                ),
                *general_information_items,
                Div(
                    HTML(
                        "<h3 class='d-flex justify-content-center'>Type 2 challenge cost estimation</h3><br>"
                    ),
                    HTML(
                        "<p>Since Type 2 challenges involve running algorithm "
                        "containers on our AWS infrastructure on a hidden test "
                        "set, we need to know how computationally expensive "
                        "your challenge will be and how much data storage your "
                        "challenge will require. The below information will "
                        "help us calculate a rough cost estimate.</p>"
                        "<p> If you are unfamiliar with what a Type 2 challenge"
                        " entails, please first read this part of our "
                        "documentation.</p> "
                        "<p>To help you fill in the below form correctly, "
                        "we have assembled example budgets here. Please take "
                        "a close look at those before proceeding to fill in "
                        "this form."
                        "</p><br>"
                    ),
                    "number_of_tasks",
                    "average_size_of_test_image",
                    "inference_time_limit",
                    HTML(
                        "<br><h4>Phase 1</h4><p>As explained here, "
                        "type 2 challenges usually consist of at least 2 phases. "
                        "The first of those tends to be a preliminary test phase,"
                        "and the second the final test phase. The number of test "
                        "images used for these phases and often the amount of "
                        "times that users can submit to them differs, which is "
                        "why we ask for separate estimates for the two phases here."
                        " Should your phase have only phase, enter 0 in all fields "
                        "for phase 2. Should your challenge have multiple tasks and "
                        "hence more than 2 phases, please provide the average numbers "
                        "across tasks for each phase below and indicate the number of "
                        "tasks above acccordingly.</p>"
                    ),
                    *phase_1_items,
                    HTML("<br><h4>Phase 2</h4>"),
                    *phase_2_items,
                    id="budget-fields",
                    css_class="border rounded px-4 pt-4 my-5",
                ),
            ),
            ButtonHolder(Submit("save", "Save")),
        )
        if (
            self.instance.challenge_type
            == self.instance.ChallengeTypeChoices.T2
        ):
            self.fields["number_of_tasks"].required = True
            self.fields["average_size_of_test_image"].required = True
            self.fields["inference_time_limit"].required = True
            self.fields[
                "phase_1_number_of_submissions_per_team"
            ].required = True
            self.fields[
                "phase_2_number_of_submissions_per_team"
            ].required = True
            self.fields["phase_1_number_of_test_images"].required = True
            self.fields["phase_2_number_of_test_images"].required = True


class ChallengeRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = ("status",)
        widgets = {
            "status": Select(choices=((True, "Approve"), (False, "Decline"),)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
