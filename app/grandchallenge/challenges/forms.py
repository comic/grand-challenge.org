from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    ButtonHolder,
    Div,
    Fieldset,
    Layout,
    Submit,
)
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget
from django_summernote.widgets import SummernoteInplaceWidget

from grandchallenge.challenges.models import (
    Challenge,
    ChallengeRequest,
    ExternalChallenge,
)
from grandchallenge.subdomains.utils import reverse_lazy

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
    "short_name",
    "contact_email",
    "abstract",
    "start_date",
    "end_date",
    "organizers",
    "affiliated_event",
    "structured_challenge_submission_form",
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
            "average_size_of_test_image_in_mb",
            "inference_time_limit_in_minutes",
            "budget_for_hosting_challenge",
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
            "title": "The name of the planned challenge.",
            "short_name": (
                "Short name that will be used in the URL "
                "(e.g., https://{short_name}.grand-challenge.org/), specific css "
                "and files if the challenge is accepted. No spaces and special "
                "characters allowed. We prefer a single word with two digits at "
                "the end indicating the year (e.g. LUNA16). See "
                "<a href='https://www.grand-challenge.org/challenges' "
                "target='_blank'>other challenges</a> for examples."
            ),
            "abstract": (
                "Provide a summary of the challenge purpose. "
                "This should include a general introduction to the "
                "topic from both a biomedical as well as from a technical point of "
                "view. From a biomedical point of view, please elaborate on the "
                "specific task at hand, how the task is currently performed "
                "(i.e., manual vs (semi-)automatic) and how an algorithm may improve "
                "this task. From a technical point of view, please mention "
                "how current state-of-the-art algorithms perform on this task "
                "(e.g., dice coefficient for segmentation tasks) and under which "
                "circumstances this performance was achieved (i.e., dataset size, "
                "modality, etc.). Finally, we kindly ask you to clearly state the "
                "envisioned technical and/or biomedical impact of the challenge."
            ),
            "challenge_type": (
                "<b>Type 1 :</b> Prediction submission - "
                "test data are open, participants run their algorithms locally "
                "and submit their predictions which are evaluated against a secret "
                "ground truth on the platform.<br>"
                "<b>Type 2:</b> Docker container submission – test data are "
                "secret, participants submit algorithms as docker "
                "containers, which are run on the secret test set on "
                "our servers and then evaluated against a secret ground "
                "truth. <br>"
                "<b>We strongly encourage Type 2 challenges.</b> "
                "For more information on both types see our <a href="
                "'https://grand-challenge.org/documentation/create-your-own-challenge/' "
                "target='_blank'> documentation</a>."
            ),
            "code_availability": (
                "Will the participants’ code be accessible after "
                "the challenge? <br>We strongly encourage open science. For Type "
                "2 challenges, algorithms will be stored on Grand Challenge and "
                "we encourage organizers to incentivize an open source policy, "
                "for example by asking participants to publish their Github repo "
                "under an <a href='https://docs.github.com/en/repositories/managing-"
                "your-repositorys-settings-and-features/customizing-your-repository/"
                "licensing-a-repository' target='_blank'> open source license</a> "
                "(e.g., Apache 2.0, MIT) and <a href='https://grand-challenge.org/"
                "documentation/linking-a-github-repository-to-your-algorithm/'>"
                "link it to their algorithm</a> on Grand Challenge."
            ),
            "data_set": (
                "Describe the training and test datasets you are planning to "
                "use and provide information on the "
                "<a href='https://creativecommons.org/licenses/' target='_blank'>"
                "license</a> of the data. <br>For Type 1 challenges, indicate where "
                "you will store the data (read about the options <a href="
                "'https://grand-challenge.org/documentation/data-storage/' "
                "target='_blank'>here</a>).<br>For Type 2 challenges, the test "
                "dataset will need to be uploaded to Grand Challenge (read more "
                "about that <a href='https://grand-challenge.org/documentation/"
                "data-storage-2/' target='_blank'>here</a>)."
            ),
            "structured_challenge_submission_form": (
                "Have you registered this challenge"
                " for a conference (e.g., MICCAI, MIDL, ISBI) "
                "<a href='https://www.biomedical-challenges.org/' target='_blank'> "
                "through this website</a>? If so, you can alternatively upload the "
                "submission PDF here and fill the below text boxes with 'See PDF'."
            ),
            "number_of_tasks": (
                "If your challenge has multiple tasks, we multiply"
                "the phase 1 and 2 cost estimates by the number of tasks. "
                "For that to work, please provide the average number of "
                "test images and the average number of submissions across "
                "tasks for the two phases below. For examples check "
                "<a href='https://grand-challenge.org/documentation/"
                "create-your-own-challenge/'>here</a>."
            ),
            "challenge_setup": (
                "Describe the challenge set-up. How many tasks "
                "and <a href='https://www.grand-challenge.org/documentation/"
                "multiple-phases-multiple-leaderboards/' target='_blank'>phases</a>"
                " does the challenge have?"
            ),
            "inference_time_limit_in_minutes": (
                "Time limit for each algorithm job in minutes. "
                "This time limit should account for everything that needs to happen "
                "for an algorithm container to process one single image, including "
                "model loading, i/o, preprocessing and inference."
            ),
        }

    def __init__(self, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.creator = creator
        self.fields["title"].required = True
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                "",
                Div(
                    HTML(
                        "<br><p>Thank you for considering to host your challenge"
                        " on our platform! </p><p>Please use this form to tell us "
                        "more about your planned challenge. "
                        "The answers you provide below will help our team of "
                        "reviewers decide whether and in what way we can "
                        "support your challenge.</p>"
                        "<p>To learn more about how challenges work on Grand "
                        "Challenge and how the request procedure is set up, "
                        "take a look at our <a href="
                        "'https://grand-challenge.org/documentation/create-your-own-challenge/'"
                        "target='_blank'>documentation</a>.</p><br>"
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
                        "your challenge submissions will be and how much data "
                        "storage your challenge requires. We will use the "
                        "below information to calculate a rough cost estimate.</p>"
                        "<p> If you are unfamiliar with what a Type 2 challenge"
                        " entails, please <a href="
                        "'https://grand-challenge.org/documentation/type-ii-challenge-setup/'"
                        "target='_blank'> first read our documentation</a>.</p> "
                        "<p>To help you fill in the below form correctly, "
                        "<a href='https://grand-challenge.org/documentation/create-your-own-challenge/'"
                        "target='_blank'> we have assembled example budgets "
                        "here</a>. Please take a close look at those before "
                        "proceeding to fill in this form.</p><br>"
                    ),
                    "number_of_tasks",
                    "average_size_of_test_image_in_mb",
                    "inference_time_limit_in_minutes",
                    "budget_for_hosting_challenge",
                    HTML(
                        "<br><p>Type 2 challenges usually consist of 2 phases. "
                        "The first of those tends to be a "
                        "<b>preliminary test phase</b>, "
                        "and the second the <b>final test phase</b>. The "
                        "number of test images used for these phases and "
                        "often the amount of times that users can submit to "
                        "them differs, which is why we ask for separate "
                        "estimates for the two phases below."
                        " Should your challenge have only phase, enter 0 in "
                        "all fields for phase 2. Should your challenge have "
                        "multiple tasks and hence more than N*2 phases, "
                        "please provide the average numbers across tasks for "
                        "each phase below and indicate the number of "
                        "tasks above accordingly. For examples of those"
                        " and other scenarios, have a look "
                        "<a href='https://grand-challenge.org/documentation/create-your-own-challenge/'"
                        "target='_blank'>at our example budget calculations</a>"
                        ".</p><h4>Phase 1</h4>"
                    ),
                    *phase_1_items,
                    HTML("<h4>Phase 2</h4>"),
                    *phase_2_items,
                    id="budget-fields",
                    css_class="border rounded px-4 pt-4 my-5",
                ),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data["start_date"] >= cleaned_data["end_date"]:
            raise ValidationError(
                "The start date needs to be before the end date."
            )

        if (
            cleaned_data["challenge_type"]
            == self.instance.ChallengeTypeChoices.T2
        ):
            if not cleaned_data["average_size_of_test_image_in_mb"]:
                raise ValidationError(
                    "For a type 2 challenge, you need to provide the average "
                    "test image size."
                )
            if not cleaned_data["inference_time_limit_in_minutes"]:
                raise ValidationError(
                    "For a type 2 challenge, you need to provide an inference "
                    "time limit."
                )
            if (
                cleaned_data["phase_1_number_of_submissions_per_team"] is None
                or cleaned_data["phase_2_number_of_submissions_per_team"]
                is None
            ):
                raise ValidationError(
                    "For a type 2 challenge, you need to provide the number of "
                    "submissions per team for each phase. Enter 0 for phase 2 "
                    "if you only have 1 phase."
                )
            if (
                cleaned_data["phase_1_number_of_test_images"] is None
                or cleaned_data["phase_2_number_of_test_images"] is None
            ):
                raise ValidationError(
                    "For a type 2 challenge, You need to provide the number of "
                    "test images for each phase. Enter 0 for phase 2 if you "
                    "only have 1 phase."
                )


class ChallengeRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            c
            for c in self.Meta.model.ChallengeRequestStatusChoices.choices
            if c[0] != self.Meta.model.ChallengeRequestStatusChoices.PENDING
        ]
        if (
            self.instance.status
            != self.instance.ChallengeRequestStatusChoices.PENDING
        ):
            self.fields["status"].widget.attrs["disabled"] = True
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Save"))
