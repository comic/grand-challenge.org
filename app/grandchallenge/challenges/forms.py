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
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.components.models import GPUTypeChoices
from grandchallenge.components.schemas import get_default_gpu_type_choices
from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.subdomains.utils import reverse_lazy

information_items = (
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
    "display_forum_link",
    "disclaimer",
    "contact_email",
)

images_items = ("banner", "logo", "social_image")

event_items = ("event_url", "workshop_date")

registration_items = (
    "use_registration_page",
    "access_request_handling",
    "registration_page_markdown",
)

HTMX_BLANK_CHOICE_KEY = "__HTMX_BLANK_CHOICE_KEY__"


class ChallengeUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    "Information",
                    *information_items,
                ),
                Tab("Images", *images_items),
                Tab("Event", *event_items),
                Tab("Registration", *registration_items),
                Tab("Teams", "use_teams"),
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    class Meta:
        model = Challenge
        fields = [
            *information_items,
            *images_items,
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
            "registration_page_markdown": MarkdownEditorInlineWidget,
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


general_information_items_1 = (
    "title",
    "short_name",
    "contact_email",
    "abstract",
    "start_date",
    "end_date",
    "organizers",
    "affiliated_event",
)
general_information_items_2 = (
    "task_types",
    "structures",
    "modalities",
    "challenge_setup",
    "data_set",
    "data_license",
    "data_license_extra",
    "submission_assessment",
    "challenge_publication",
    "code_availability",
)
phase_1_items = (
    "phase_1_number_of_submissions_per_team",
    "phase_1_number_of_test_images",
)
phase_2_items = (
    "phase_2_number_of_submissions_per_team",
    "phase_2_number_of_test_images",
)
structured_challenge_submission_help_text = (
    "If you have uploaded a PDF or "
    "provided the DOI for your structured "
    "challenge submission form above, "
    "you can enter 'See structured submission form' here."
)


class ChallengeRequestForm(forms.ModelForm):
    algorithm_selectable_gpu_type_choices = forms.MultipleChoiceField(
        initial=get_default_gpu_type_choices(),
        choices=[
            (choice.value, choice.label)
            for choice in [
                GPUTypeChoices.NO_GPU,
                GPUTypeChoices.T4,
                GPUTypeChoices.A10G,
            ]
        ],
        widget=forms.CheckboxSelectMultiple,
        label="Selectable GPU types for algorithm jobs",
        help_text="The GPU type choices that participants will be able to select for "
        "their algorithm inference jobs.",
    )

    class Meta:
        model = ChallengeRequest
        fields = (
            *general_information_items_1,
            "structured_challenge_submission_form",
            "structured_challenge_submission_doi",
            *general_information_items_2,
            "expected_number_of_teams",
            "number_of_tasks",
            "average_size_of_test_image_in_mb",
            "inference_time_limit_in_minutes",
            "algorithm_selectable_gpu_type_choices",
            "algorithm_maximum_settable_memory_gb",
            "algorithm_inputs",
            "algorithm_outputs",
            *phase_1_items,
            *phase_2_items,
            "challenge_fee_agreement",
            "comments",
        )
        widgets = {
            "start_date": forms.TextInput(attrs={"type": "date"}),
            "end_date": forms.TextInput(attrs={"type": "date"}),
        }
        labels = {
            "short_name": "Acronym",
            "data_license": "We agree to publish the data set for this challenge under a CC-BY license.",
            "phase_1_number_of_submissions_per_team": "Expected number of submissions per team to Phase 1",
            "phase_2_number_of_submissions_per_team": "Expected number of submissions per team to Phase 2",
            "inference_time_limit_in_minutes": "Average algorithm job run time in minutes",
            "algorithm_maximum_settable_memory_gb": "Maximum memory for algorithm jobs in GB",
            "structured_challenge_submission_doi": "DOI",
            "structured_challenge_submission_form": "PDF",
            "challenge_fee_agreement": format_html(
                "I confirm that I have read and understood the <a href='{}'>pricing policy</a> for running a challenge.",
                "https://grand-challenge.org/challenge-policy-and-pricing/",
            ),
        }
        help_texts = {
            "title": "The name of the planned challenge.",
            "short_name": (
                "Acronym of your challenge title that will be used in the URL "
                "(e.g., https://{acronym}.grand-challenge.org/), specific css "
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
            "code_availability": (
                "Will the participants’ code be accessible after "
                "the challenge? <br>We strongly encourage open science. Algorithms "
                "submitted as challenge solutions will therefore be stored on Grand Challenge and "
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
                f"{structured_challenge_submission_help_text} Otherwise, please "
                f"describe the training and test datasets you are planning to "
                f"use. <br>In order to evaluate the submitted algorithms, the test dataset will need to be "
                f"uploaded to Grand Challenge (read more about that <a href='https://grand-challenge.org/documentation/"
                f"data-storage/' target='_blank'>here</a>)."
            ),
            "number_of_tasks": (
                "If your challenge has multiple tasks, we multiply "
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
                "The average time that you expect an algorithm job to take in minutes. "
                "This time estimate should account for everything that needs to happen "
                "for an algorithm container to process <u>one single image, including "
                "model loading, i/o, preprocessing and inference.</u>"
            ),
            "data_license": (
                "In the spirit of open science, we ask that the <b>public training "
                "data</b> are released under a "
                "<a href='https://creativecommons.org/licenses/' target='_blank'>"
                "CC-BY license</a>. Note that this does not apply to the secret test "
                "data used to evaluate algorithm submissions. Read more about this <a href='"
                "https://grand-challenge.org/documentation/data-storage/'>here</a>."
            ),
            "phase_1_number_of_test_images": (
                "Number of test images for this phase. If you're <a href="
                "'https://grand-challenge.org/documentation/create-your-own-challenge/#budget-batched-images'>"
                "bundling images</a>, enter the number of batches (not the number of single images)."
            ),
            "phase_2_number_of_test_images": (
                "Number of test images for this phase. If you're <a href="
                "'https://grand-challenge.org/documentation/create-your-own-challenge/#budget-batched-images'>"
                "bundling images</a>, enter the number of batches (not the number of single images). "
                "Enter 0 here if you only have one phase."
            ),
            "average_size_of_test_image_in_mb": (
                "Average size of test image in MB. If you're <a href="
                "'https://grand-challenge.org/documentation/create-your-own-challenge/#budget-batched-images'>"
                "bundling images</a>, provide the size of the batch (not the size of a single image)."
            ),
            "phase_1_number_of_submissions_per_team": (
                "How many submissions do you expect per team to this phase? "
                "You can enforce a submission limit in the settings for each phase "
                "to control this."
            ),
            "phase_2_number_of_submissions_per_team": (
                "How many submissions do you expect per team to this phase? "
                "You can enforce a submission limit in the settings for each phase "
                "to control this. Enter 0 here if you only have one phase."
            ),
            "submission_assessment": (
                f"{structured_challenge_submission_help_text} Otherwise, "
                f"please define the metrics you will use "
                "to assess and rank participants’ submissions."
            ),
            "challenge_publication": (
                f"{structured_challenge_submission_help_text} Otherwise, "
                f"please indicate if you plan to coordinate a publication "
                f"of the challenge results."
            ),
        }

    def __init__(self, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.creator = creator
        self.fields["title"].required = True
        self.fields["challenge_fee_agreement"].required = True
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
                        "<p>Before you fill out this form, please read our <a href="
                        "'https://grand-challenge.org/documentation/challenges/'"
                        "target='_blank'>challenge documentation</a> and our <a href="
                        "'https://grand-challenge.org/challenge-policy-and-pricing/'"
                        "target='_blank'>challenge pricing policy</a>.</p><br>"
                    ),
                ),
                *general_information_items_1,
                Div(
                    HTML(
                        "<p class='mb-0'>Structured challenge submission form </p>"
                        "<small class='text-muted mb-2'> Have you registered this challenge "
                        "for a conference (e.g., MICCAI, ISBI) <a href='https://www.biomedical-challenges.org/' target='_blank'> "
                        "through this website</a>? If so, please provide the DOI for your submission form, or"
                        " upload the submission PDF here. If you want to <a href='https://www.midl.io/'>organize your challenge with MIDL</a>, "
                        "you <u>must</u> fill out the <a href='https://www.biomedical-challenges.org/'>structured submission form</a> and upload the PDF. "
                        "If you have added a link or PDF, please fill the below text boxes with 'See structured submission form'.</small>"
                    ),
                    Div(
                        "structured_challenge_submission_doi",
                        css_class="col-5 pl-0",
                    ),
                    Div(
                        HTML("<p>or</p>"),
                        css_class="col-1 pl-0 d-flex align-items-center justify-content-center",
                    ),
                    Div(
                        "structured_challenge_submission_form",
                        css_class="col-5 pl-0",
                    ),
                    css_class="container row m-0 p-0 justify-content-between",
                ),
                *general_information_items_2,
                Div(
                    "algorithm_inputs",
                    "algorithm_outputs",
                ),
                Div(
                    HTML(
                        "<h3 class='d-flex justify-content-center'>Compute and storage cost estimation</h3><br>"
                    ),
                    HTML(
                        format_html(
                            (
                                "<p>Challenge submissions require running algorithm "
                                "containers on hidden test data, and hence require "
                                "storage and compute capacity. Please review our "
                                "<a href='{policy_link}' target='_blank'>"
                                "challenge pricing policy</a> before continuing.</p>"
                                "<p>The information you provide below will serve as "
                                "a starting point for estimating the compute and "
                                "storage costs for your challenge. "
                                "Our team will review and, if necessary, adjust "
                                "these estimates with you to establish a cost "
                                "structure that aligns with your needs.</p>"
                                "<p>If you are new to Grand Challenge, please "
                                "<a href='{documentation_link}' target='_blank'> "
                                "refer to our challenge documentation</a> "
                                "for guidance. We have also prepared "
                                "<a href='{link_to_examples}' target='_blank'> "
                                "example budgets </a> to help you complete this "
                                "form accurately.</p><br>"
                            ),
                            policy_link="https://grand-challenge.org/challenge-policy-and-pricing/",
                            documentation_link="https://grand-challenge.org/documentation/challenge-setup/",
                            link_to_examples="https://grand-challenge.org/documentation/create-your-own-challenge/#compute-and-storage-costs",
                        )
                    ),
                    "expected_number_of_teams",
                    "number_of_tasks",
                    "average_size_of_test_image_in_mb",
                    "inference_time_limit_in_minutes",
                    "algorithm_selectable_gpu_type_choices",
                    "algorithm_maximum_settable_memory_gb",
                    HTML(
                        format_html(
                            (
                                "<br><p>Challenges usually consist of 2 phases: "
                                "a <b>preliminary debug phase</b>, and "
                                "a <b>final test phase</b>. "
                                "The number of test images used for these "
                                "phases and often the amount of times that "
                                "users can submit to them differs, which is "
                                "why we ask for separate estimates for the two "
                                "phases below. "
                                "Should your challenge have multiple tasks "
                                "and hence more than 2 phases, "
                                "please provide the average numbers across tasks for "
                                "each phase below and indicate the number of "
                                "tasks above accordingly. For examples of those "
                                "and other scenarios, have a look "
                                "<a href='{documentation_link}' target='_blank'>"
                                "at our example cost calculations</a>"
                                ".</p><h4>Phase 1</h4>"
                            ),
                            documentation_link="https://grand-challenge.org/documentation/create-your-own-challenge/",
                        )
                    ),
                    *phase_1_items,
                    HTML("<h4>Phase 2</h4>"),
                    *phase_2_items,
                    css_class="border rounded px-4 pt-4 my-5",
                ),
                "challenge_fee_agreement",
                "comments",
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("start_date")
        end = cleaned_data.get("end_date")
        if start and end and start >= end:
            raise ValidationError(
                "The start date needs to be before the end date."
            )
        if (
            "algorithm_inputs" not in cleaned_data.keys()
            or "algorithm_outputs" not in cleaned_data.keys()
        ):
            raise ValidationError(
                "Please describe what inputs and outputs the algorithms submitted to your challenge take and produce."
            )
        return cleaned_data


class ChallengeRequestStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].label = False
        self.fields["status"].choices = [
            c
            for c in self.Meta.model.ChallengeRequestStatusChoices.choices
            if c[0] != self.Meta.model.ChallengeRequestStatusChoices.PENDING
        ]
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                Div("status", css_class="col-lg-8 px-0 mt-3"),
                Div(
                    ButtonHolder(
                        Submit("save", "Save", css_class="btn-sm mt-lg-1")
                    ),
                    css_class="col-lg-4 pb-0 mt-lg-3 pl-lg-2",
                ),
                css_class="row container m-0 p-0",
            )
        )
        self.helper.attrs.update(
            {
                "hx-post": reverse(
                    "challenges:requests-status-update",
                    kwargs={"pk": self.instance.pk},
                ),
                # use 'this' to display form errors in place, when the form is valid,
                # a page refresh will be triggered (by setting HX-Refresh to true)
                "hx-target": "this",
                "hx-swap": "outerHTML",
            }
        )
        if (
            self.instance.status
            != self.instance.ChallengeRequestStatusChoices.PENDING
        ):
            self.fields["status"].disabled = True

    def clean_status(self):
        status = self.cleaned_data.get("status")

        if (
            status == self.instance.ChallengeRequestStatusChoices.ACCEPTED
            and Challenge.objects.filter(
                short_name=self.instance.short_name
            ).exists()
        ):
            raise ValidationError(
                "There already is a challenge with this name. "
                "Please contact support to accept this request.",
            )

        return status


class ChallengeRequestBudgetUpdateForm(forms.ModelForm):
    algorithm_selectable_gpu_type_choices = forms.MultipleChoiceField(
        choices=[
            (HTMX_BLANK_CHOICE_KEY, GPUTypeChoices.NO_GPU.label),
            (GPUTypeChoices.T4, GPUTypeChoices.T4.label),
            (GPUTypeChoices.A10G, GPUTypeChoices.A10G.label),
        ],
        widget=forms.CheckboxSelectMultiple,
        label="Selectable GPU types for algorithm jobs",
        help_text="The GPU type choices that participants will be able to select for "
        "their algorithm inference jobs.",
    )

    class Meta:
        model = ChallengeRequest
        fields = (
            "expected_number_of_teams",
            "number_of_tasks",
            "inference_time_limit_in_minutes",
            "algorithm_selectable_gpu_type_choices",
            "algorithm_maximum_settable_memory_gb",
            "average_size_of_test_image_in_mb",
            "phase_1_number_of_submissions_per_team",
            "phase_1_number_of_test_images",
            "phase_2_number_of_submissions_per_team",
            "phase_2_number_of_test_images",
        )
        labels = {
            "phase_1_number_of_submissions_per_team": "Expected number of submissions per team to Phase 1",
            "phase_2_number_of_submissions_per_team": "Expected number of submissions per team to Phase 2",
            "inference_time_limit_in_minutes": "Average algorithm job run time in minutes",
            "algorithm_maximum_settable_memory_gb": "Maximum memory for algorithm jobs in GB",
        }
        help_texts = {
            "inference_time_limit_in_minutes": (
                "The average time that you expect an algorithm job to take in minutes. "
                "This time estimate should account for everything that needs to happen "
                "for an algorithm container to process <u>one single image, including "
                "model loading, i/o, preprocessing and inference.</u>"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "" in (
            initial := self.instance.algorithm_selectable_gpu_type_choices
        ):
            initial[initial.index("")] = HTMX_BLANK_CHOICE_KEY
            self.fields["algorithm_selectable_gpu_type_choices"].initial = (
                initial
            )
        self.helper = FormHelper(self)
        self.helper.form_id = "budget"
        self.helper.attrs.update(
            {
                "hx-post": reverse(
                    "challenges:requests-budget-update",
                    kwargs={"pk": self.instance.pk},
                ),
                "hx-target": "#budget",
                "hx-swap": "outerHTML",
            }
        )
        self.helper.layout.append(Submit("save", "Save"))

    def clean_algorithm_selectable_gpu_type_choices(self):
        data = self.cleaned_data.get(
            "algorithm_selectable_gpu_type_choices", []
        )
        if HTMX_BLANK_CHOICE_KEY in data:
            data[data.index(HTMX_BLANK_CHOICE_KEY)] = ""
        return data
