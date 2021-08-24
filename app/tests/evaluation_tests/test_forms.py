import pytest

from grandchallenge.evaluation.forms import SubmissionForm
from grandchallenge.evaluation.models import Phase
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.evaluation_tests.factories import PhaseFactory
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestSubmissionForm:
    def test_setting_predictions_file(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=Phase.SubmissionKind.CSV),
        )

        assert "algorithm" not in form.fields
        assert "chunked_upload" in form.fields

    def test_setting_algorithm(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=Phase.SubmissionKind.ALGORITHM),
        )

        assert "algorithm" in form.fields
        assert "chunked_upload" not in form.fields

    def test_no_algorithm_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=Phase.SubmissionKind.ALGORITHM),
            data={"algorithm": ""},
        )

        assert form.errors["algorithm"] == ["This field is required."]

    def test_algorithm_no_permission(self):
        alg = AlgorithmFactory()

        form = SubmissionForm(
            user=UserFactory(),
            phase=PhaseFactory(submission_kind=Phase.SubmissionKind.ALGORITHM),
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
            phase=PhaseFactory(submission_kind=Phase.SubmissionKind.ALGORITHM),
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

        ai = AlgorithmImageFactory(ready=True, algorithm=alg)
        AlgorithmJobFactory(algorithm_image=ai, status=4)

        p = PhaseFactory(submission_kind=Phase.SubmissionKind.ALGORITHM)

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
            phase=PhaseFactory(creator_must_be_verified=True),
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
