import pytest
from factory.django import ImageField

from grandchallenge.algorithms.forms import AlgorithmForPhaseForm
from grandchallenge.evaluation.forms import SubmissionForm
from grandchallenge.evaluation.models import Phase
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import (
    UserFactory,
    WorkstationConfigFactory,
    WorkstationFactory,
)
from tests.hanging_protocols_tests.factories import HangingProtocolFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestSubmissionForm:
    def test_setting_predictions_file(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=SubmissionKindChoices.CSV),
        )

        assert "algorithm" not in form.fields
        assert "user_upload" in form.fields

    def test_setting_algorithm(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
        )

        assert "algorithm" in form.fields
        assert "user_upload" not in form.fields

    def test_no_algorithm_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": ""},
        )

        assert form.errors["algorithm"] == ["This field is required."]

    def test_algorithm_no_permission(self):
        alg = AlgorithmFactory()

        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": alg.pk},
        )

        assert form.errors["algorithm"] == [
            "Select a valid choice. That choice is not one of the available choices."
        ]

    def test_algorithm_with_permission_not_ready(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        alg.inputs.clear()
        alg.outputs.clear()

        form = SubmissionForm(
            user=user,
            phase=PhaseFactory(
                submission_kind=SubmissionKindChoices.ALGORITHM
            ),
            data={"algorithm": alg.pk},
        )

        assert form.errors["algorithm"] == [
            "This algorithm does not have a usable container image. "
            "Please add one and try again."
        ]

    def test_algorithm_with_permission(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        alg.inputs.clear()
        alg.outputs.clear()

        ai = AlgorithmImageFactory(
            is_manifest_valid=True, is_in_registry=True, algorithm=alg
        )
        AlgorithmJobFactory(algorithm_image=ai, status=4)

        p = PhaseFactory(
            submission_kind=SubmissionKindChoices.ALGORITHM,
            submissions_limit_per_user_per_period=10,
        )

        form = SubmissionForm(
            user=user,
            phase=p,
            data={"algorithm": alg.pk, "creator": user, "phase": p},
        )

        assert form.errors == {}
        assert "algorithm" not in form.errors
        assert form.is_valid()

    def test_user_no_verification(self):
        user = UserFactory()

        form = SubmissionForm(
            user=user,
            phase=PhaseFactory(creator_must_be_verified=True),
            data={"creator": user},
        )

        assert form.errors["creator"] == [
            "You must verify your account before you can make a "
            "submission to this phase. Please "
            '<a href="https://testserver/verifications/create/"> '
            "request verification here</a>."
        ]

    @pytest.mark.parametrize("is_verified", (True, False))
    def test_user_with_verification(self, is_verified):
        user = UserFactory()
        VerificationFactory(user=user, is_verified=is_verified)

        form = SubmissionForm(
            user=user,
            phase=PhaseFactory(
                creator_must_be_verified=True,
                submissions_limit_per_user_per_period=10,
            ),
            data={"creator": user},
        )
        assert bool("creator" in form.errors) is not is_verified


@pytest.mark.django_db
class TestSubmissionFormOptions:
    def test_no_supplementary_url(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.OFF),
        )
        assert "supplementary_url" not in form.fields

    def test_supplementary_url_optional(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.OPTIONAL),
        )
        assert "supplementary_url" in form.fields
        assert form.fields["supplementary_url"].required is False

    def test_supplementary_url_required(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(supplementary_url_choice=Phase.REQUIRED),
        )
        assert "supplementary_url" in form.fields
        assert form.fields["supplementary_url"].required is True

    def test_supplementary_url_label(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                supplementary_url_choice=Phase.OPTIONAL,
                supplementary_url_label="TEST",
            ),
        )
        assert form.fields["supplementary_url"].label == "TEST"

    def test_supplementary_url_help_text(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(
                supplementary_url_choice=Phase.OPTIONAL,
                supplementary_url_help_text="<script>TEST</script>",
            ),
        )
        assert (
            form.fields["supplementary_url"].help_text
            == "&lt;script&gt;TEST&lt;/script&gt;"
        )


def test_algorithm_for_phase_form():
    form = AlgorithmForPhaseForm(
        workstation_config=WorkstationConfigFactory.build(),
        hanging_protocol=HangingProtocolFactory.build(),
        view_content="{}",
        display_editors=True,
        contact_email="test@test.com",
        workstation=WorkstationFactory.build(),
        inputs=[ComponentInterfaceFactory.build()],
        outputs=[ComponentInterfaceFactory.build()],
        structures=[],
        modalities=[],
        logo=ImageField(filename="test.jpeg"),
    )

    assert form.fields["inputs"].disabled
    assert form.fields["outputs"].disabled
    assert form.fields["workstation_config"].disabled
    assert form.fields["hanging_protocol"].disabled
    assert form.fields["view_content"].disabled
    assert form.fields["display_editors"].disabled
    assert form.fields["workstation"].disabled
    assert form.fields["structures"].disabled
    assert form.fields["modalities"].disabled
    assert form.fields["contact_email"].disabled
    assert form.fields["logo"].disabled
    assert not form.fields["title"].disabled
    assert not form.fields["description"].disabled
    assert not form.fields["image_requires_gpu"].disabled
    assert not form.fields["image_requires_memory_gb"].disabled

    assert {
        form.fields["inputs"],
        form.fields["outputs"],
        form.fields["workstation_config"],
        form.fields["hanging_protocol"],
        form.fields["view_content"],
        form.fields["display_editors"],
        form.fields["workstation"],
        form.fields["structures"],
        form.fields["modalities"],
        form.fields["contact_email"],
        form.fields["logo"],
    } == {field.field for field in form.hidden_fields()}

    assert {
        form.fields["title"],
        form.fields["description"],
        form.fields["image_requires_gpu"],
        form.fields["image_requires_memory_gb"],
    } == {field.field for field in form.visible_fields()}
