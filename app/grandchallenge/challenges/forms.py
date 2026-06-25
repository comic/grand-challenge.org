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
from django.forms import Textarea
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import format_lazy
from django_select2.forms import Select2MultipleWidget

from grandchallenge.challenges.models import Challenge, ChallengeRequest
from grandchallenge.core.forms import SaveFormInitMixin
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


general_required_information = (
    "title",
    "short_name",
    "contact_email",
    "abstract",
    "start_date",
    "end_date",
    "organizers",
    "challenge_setup",
    "challenge_fee_agreement",
)
general_information = (
    "comments",
    "affiliated_event",
    "task_types",
    "structures",
    "modalities",
)
challenge_details = (
    "data_set",
    "data_license",
    "data_license_extra",
    "submission_assessment",
    "challenge_publication",
    "code_availability",
    "algorithm_inputs",
    "algorithm_outputs",
)
structured_challenge_submission_help_text = (
    "If you have uploaded a PDF or "
    "provided the DOI for your structured "
    "challenge submission form above, "
    "you can enter 'See structured submission form' here."
)


class ChallengeRequestForm(SaveFormInitMixin, forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = (
            "title",
            "short_name",
            "contact_email",
        )
        labels = {
            "short_name": "Acronym",
        }
        help_texts = {
            "title": "The name of the planned challenge.",
            "short_name": (
                "Acronym of your challenge title that will be used in the URL "
                "(e.g., https://{acronym}.grand-challenge.org/). No spaces and special "
                "characters allowed. We prefer a single word with two digits at "
                "the end indicating the year (e.g. LUNA26). See "
                "<a href='https://www.grand-challenge.org/challenges' "
                "target='_blank'>other challenges</a> for examples."
            ),
        }

    def __init__(self, creator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.creator = creator
        self.fields["title"].required = True


challenge_setup_template_text = """\
Please describe the runtime requirements, the amount of test data, and the participation limits for each phase.
This information will be used to calculate a budget estimate. See below example.

## Runtime Requirements
- Participant algorithm max. runtime: 5 minutes
- Participant algorithm max. DRAM: 32 GB
- Participant algorithm GPU types: A10G or T4 or None
- Evaluation method max. runtime: 42 minutes
- Evaluation method max. DRAM: 32 GB
- Evaluation method GPU types: A10G

If some phases have different requirements, please detail them.

## Test data
- Total size of all test cases: 5.4 GB
- Number of cases: 21
- Average output size per case: 100 MB

## Phase 1 - debug
- Expected total number of teams: 20
- Number of submissions per team: 3
- Number of test cases: 1

## Phase 2 - test
- Expected total number of teams: 20
- Number of submissions per team: 1
- Number of test cases: 20\
"""


class ChallengeRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = (
            *general_required_information,
            *general_information,
            "structured_challenge_submission_form",
            "structured_challenge_submission_doi",
            *challenge_details,
            "algorithm_inputs",
            "algorithm_outputs",
        )
        widgets = {
            "start_date": forms.TextInput(attrs={"type": "date"}),
            "end_date": forms.TextInput(attrs={"type": "date"}),
            "abstract": forms.Textarea(attrs={"rows": 4}),
            "organizers": forms.Textarea(attrs={"rows": 3}),
            "comments": forms.Textarea(attrs={"rows": 2}),
            "challenge_setup": forms.Textarea(
                attrs={
                    "rows": len(challenge_setup_template_text.splitlines()),
                }
            ),
        }
        labels = {
            "short_name": "Acronym",
            "data_license": "We agree to publish the data set for this challenge under a CC-BY license.",
            "structured_challenge_submission_doi": "DOI",
            "structured_challenge_submission_form": "PDF",
            "challenge_fee_agreement": format_html(
                "I confirm that I have read and understood the <a href='{}'>pricing policy</a> for running a challenge.",
                "https://grand-challenge.org/challenge-policy-and-pricing/",
            ),
            "challenge_setup": "Challenge technical setup",
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = True

        if not self.instance.challenge_setup:
            self.initial["challenge_setup"] = challenge_setup_template_text

        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Fieldset(
                "General Information - Required",
                *general_required_information,
                css_class="border rounded px-2 my-4",
            ),
            Fieldset(
                "General Information - Optional",
                *general_information,
                css_class="border rounded px-2 my-4",
            ),
            Div(
                HTML(
                    "<i class='fas fa-info-circle px-2'></i> Provide the required information by either uploading a pre-existing form OR filling the detailed challenge information below."
                ),
                css_class="alert alert-info py-4",
            ),
            Fieldset(
                "Structured Challenge Submission from a Pre-Existing Form",
                Div(
                    HTML(
                        "<small class='text-muted mb-2'> Have you registered this challenge "
                        "for a conference (e.g., MICCAI, ISBI) <a href='https://www.biomedical-challenges.org/' target='_blank'> "
                        "through this website</a>? If so, please provide the DOI for your submission form, or"
                        " upload the submission PDF here. If you want to <a href='https://www.midl.io/'>organize your challenge with MIDL</a>, "
                        "you <u>must</u> fill out the <a href='https://www.biomedical-challenges.org/'>structured submission form</a> and upload the PDF."
                        "</small>"
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
                css_class="border rounded pt-2 px-2 my-4 bg-gray-100",
            ),
            HTML("<h4 class='text-center'>OR</h4>"),
            Fieldset(
                "Detailed Challenge Information",
                *challenge_details,
                css_class="border rounded pt-2 px-2 my-1 bg-gray-100",
            ),
            ButtonHolder(Submit("save", "Save")),
        )

    def clean(self):
        cleaned_data = super().clean()

        if (
            self.instance.status
            != self.instance.ChallengeRequestStatusChoices.DRAFT
        ):
            raise ValidationError(
                "Only challenge requests in draft status can be edited. Please contact support if you want to make changes to this request.",
            )

        return cleaned_data

    def clean_challenge_setup(self):
        challenge_setup = self.cleaned_data.get("challenge_setup")

        if (
            challenge_setup
            and challenge_setup.strip().splitlines()
            == challenge_setup_template_text.strip().splitlines()
        ):
            return ""
        else:
            return challenge_setup


class ChallengeRequestStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = ChallengeRequest
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if (
            self.instance.status
            == self.instance.ChallengeRequestStatusChoices.DRAFT
        ):
            self.fields["status"].choices = [
                (
                    self.Meta.model.ChallengeRequestStatusChoices.PENDING.value,
                    self.Meta.model.ChallengeRequestStatusChoices.PENDING.label,
                ),
            ]
        elif (
            self.instance.status
            == self.instance.ChallengeRequestStatusChoices.PENDING
        ):
            self.fields["status"].choices = [
                (
                    self.Meta.model.ChallengeRequestStatusChoices.ACCEPTED.value,
                    self.Meta.model.ChallengeRequestStatusChoices.ACCEPTED.label,
                ),
                (
                    self.Meta.model.ChallengeRequestStatusChoices.REJECTED.value,
                    self.Meta.model.ChallengeRequestStatusChoices.REJECTED.label,
                ),
                (
                    self.Meta.model.ChallengeRequestStatusChoices.CANCELLED.value,
                    self.Meta.model.ChallengeRequestStatusChoices.CANCELLED.label,
                ),
            ]
        else:
            self.fields["status"].choices = []
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
    class Meta:
        model = ChallengeRequest
        fields = (
            "task_ids",
            "algorithm_selectable_gpu_type_choices",
            "algorithm_maximum_settable_memory_gb",
            "average_size_test_case_mb_for_tasks",
            "inference_time_average_minutes_for_tasks",
            "task_id_for_phases",
            "number_of_teams_for_phases",
            "number_of_submissions_per_team_for_phases",
            "number_of_test_cases_for_phases",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget = Textarea(attrs={"rows": 1})
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
        self.helper.layout = Layout(
            HTML("<h2>Update budget fields</h2>"),
            Fieldset(
                "Tasks",
                "task_ids",
                "algorithm_selectable_gpu_type_choices",
                "algorithm_maximum_settable_memory_gb",
                "average_size_test_case_mb_for_tasks",
                "inference_time_average_minutes_for_tasks",
                css_class="border rounded px-2 my-4",
            ),
            Fieldset(
                "Phases",
                "task_id_for_phases",
                "number_of_teams_for_phases",
                "number_of_submissions_per_team_for_phases",
                "number_of_test_cases_for_phases",
                css_class="border rounded px-2 my-4",
            ),
            ButtonHolder(
                Submit("Save", "Save"),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()

        if not self.errors:
            task_ids = cleaned_data.get("task_ids")
            task_id_for_phases = cleaned_data.get("task_id_for_phases")

            self._clean_task_lists_equal_length(cleaned_data)
            self._clean_task_id_for_phases(task_ids, task_id_for_phases)
            self._clean_phases_lists_equal_length(
                task_id_for_phases, cleaned_data
            )
            self._clean_later_phases_not_more_teams_or_submissions(
                task_id_for_phases, cleaned_data
            )

        return cleaned_data

    def _clean_task_lists_equal_length(self, cleaned_data):
        task_ids = cleaned_data.get("task_ids")

        for field_name in (
            "average_size_test_case_mb_for_tasks",
            "inference_time_average_minutes_for_tasks",
        ):
            field_value = cleaned_data.get(field_name)
            if len(task_ids) != len(field_value):
                self.add_error(
                    field_name, "Must be of equal length as number of tasks."
                )

    def _clean_task_id_for_phases(self, task_ids, task_id_for_phases):
        if not set(task_id_for_phases).issubset(task_ids):
            self.add_error(
                "task_id_for_phases", "Ids must be defined in task ids."
            )
        elif set(task_id_for_phases) != set(task_ids):
            self.add_error("task_id_for_phases", "Not all task ids are used.")

    def _clean_phases_lists_equal_length(
        self, task_id_for_phases, cleaned_data
    ):
        all_phases_list_equal_length = True

        for field_name in (
            "number_of_teams_for_phases",
            "number_of_submissions_per_team_for_phases",
            "number_of_test_cases_for_phases",
        ):
            field_value = cleaned_data[field_name]
            if len(task_id_for_phases) != len(field_value):
                self.add_error(
                    field_name, "Must be of equal length as number of phases."
                )
                all_phases_list_equal_length = False

        if not all_phases_list_equal_length:
            raise ValidationError(
                "All fields defining phases must be of equal length."
            )

    def _clean_later_phases_not_more_teams_or_submissions(
        self, task_id_for_phases, cleaned_data
    ):
        for field_name in (
            "number_of_teams_for_phases",
            "number_of_submissions_per_team_for_phases",
        ):
            field_value = cleaned_data[field_name]
            for idx in range(1, len(task_id_for_phases)):
                if (
                    task_id_for_phases[idx] == task_id_for_phases[idx - 1]
                    and field_value[idx] > field_value[idx - 1]
                ):
                    self.add_error(
                        field_name,
                        "Later phases in a task may not have more submissions than earlier phases.",
                    )


class ChallengeRequestBudgetCalculatorForm(ChallengeRequestBudgetUpdateForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_id = "budget-form"
        self.helper.attrs.update(
            {
                "hx-post": reverse("challenges:requests-budget-calculator"),
                "hx-trigger": "load, input from:#budget-form delay:300ms",
                "hx-target": "#budget",
                "hx-swap": "innerHTML",
            }
        )
