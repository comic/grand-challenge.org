import pytest

from grandchallenge.evaluation.forms import SubmissionForm
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.factories import UserFactory
from tests.verification_tests.factories import VerificationFactory


@pytest.mark.django_db
class TestSubmissionForm:
    def test_setting_predictions_file(self):
        form = SubmissionForm(user=UserFactory(), algorithm_submission=False)

        assert "algorithm" not in form.fields
        assert "chunked_upload" in form.fields

    def test_setting_algorithm(self):
        form = SubmissionForm(user=UserFactory(), algorithm_submission=True)

        assert "algorithm" in form.fields
        assert "chunked_upload" not in form.fields

    def test_no_algorithm_selection(self):
        form = SubmissionForm(
            user=UserFactory(),
            algorithm_submission=True,
            data={"algorithm": ""},
        )

        assert form.errors["algorithm"] == ["This field is required."]

    def test_algorithm_no_permission(self):
        alg = AlgorithmFactory()

        form = SubmissionForm(
            user=UserFactory(),
            algorithm_submission=True,
            data={"algorithm": alg.pk},
        )

        assert form.errors["algorithm"] == [
            "Select a valid choice. That choice is not one of the available choices."
        ]

    def test_algorithm_with_permission_not_ready(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)

        form = SubmissionForm(
            user=user, algorithm_submission=True, data={"algorithm": alg.pk},
        )

        assert form.errors["algorithm"] == [
            "This algorithm does not have a usable container image. "
            "Please add one and try again."
        ]

    def test_algorithm_with_permission(self):
        user = UserFactory()
        alg = AlgorithmFactory()
        alg.add_editor(user=user)
        AlgorithmImageFactory(ready=True, algorithm=alg)

        form = SubmissionForm(
            user=user,
            algorithm_submission=True,
            data={"algorithm": alg.pk, "creator": user},
        )

        assert "algorithm" not in form.errors
        assert form.is_valid()

    def test_user_no_verification(self):
        user = UserFactory()

        form = SubmissionForm(
            user=user, creator_must_be_verified=True, data={"creator": user}
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
            user=user, creator_must_be_verified=True, data={"creator": user}
        )

        assert bool("creator" in form.errors) is not is_verified
