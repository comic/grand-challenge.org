import time

import pytest
from django.test import TestCase, override_settings

from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.serializers import ExternalEvaluationSerializer
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


def create_claimable_evaluation():
    challenge = ChallengeFactory()
    p1, p2 = PhaseFactory.create_batch(
        2, challenge=challenge, submission_kind=SubmissionKindChoices.ALGORITHM
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    for phase in [p1, p2]:
        phase.algorithm_outputs.set([ci1])
        phase.algorithm_inputs.set([ci2])
    p2.external_evaluation = True
    p2.parent = p1
    p2.save()
    ai = AlgorithmImageFactory(
        algorithm=AlgorithmFactory(),
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    ai.algorithm.inputs.set([ci1])
    ai.algorithm.inputs.set([ci2])

    return EvaluationFactory(
        submission__algorithm_image=ai, submission__phase=p2, method=None
    )


def get_user_groups(evaluation):
    external_evaluator, challenge_admin, challenge_participant = (
        UserFactory.create_batch(3)
    )
    challenge = evaluation.submission.phase.challenge
    challenge.add_admin(user=challenge_admin)
    challenge.add_participant(user=challenge_participant)
    challenge.external_evaluators_group.user_set.add(external_evaluator)

    return [external_evaluator, challenge_admin, challenge_participant]


@pytest.mark.django_db
def test_claimable_evaluations(client):
    e1 = create_claimable_evaluation()
    assert e1.status == Evaluation.PENDING

    e2 = EvaluationFactory(
        submission__phase=e1.submission.phase,
        submission__algorithm_image=e1.submission.algorithm_image,
        method=None,
    )
    e2.status = Evaluation.EXECUTING
    e2.save()

    EvaluationFactory(submission__phase=e1.submission.phase.parent)

    external_evaluator, challenge_admin, challenge_participant = (
        get_user_groups(e1)
    )

    for user in [challenge_admin, challenge_participant]:
        response = get_view_for_user(
            viewname="api:evaluation-claimable-evaluations",
            client=client,
            user=user,
            content_type="application/json",
        )
        assert response.status_code == 200
        # empty list since they don't have the claim evaluation
        # permission for any evaluations
        assert response.json() == []

    response = get_view_for_user(
        viewname="api:evaluation-claimable-evaluations",
        client=client,
        user=external_evaluator,
        content_type="application/json",
    )
    assert response.status_code == 200
    # only e1 is claimable
    assert response.json() == [
        ExternalEvaluationSerializer(
            e1, context={"request": response.wsgi_request}
        ).data
    ]


@pytest.mark.django_db
def test_claim_evaluation(client):
    eval = create_claimable_evaluation()

    external_evaluator, challenge_admin, challenge_participant = (
        get_user_groups(eval)
    )

    for user in [challenge_admin, challenge_participant]:
        response = get_view_for_user(
            viewname="api:evaluation-claim",
            client=client,
            method=client.patch,
            user=user,
            reverse_kwargs={"pk": eval.pk},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert "You do not have permission to perform this action." in str(
            response.json()
        )

    response = get_view_for_user(
        viewname="api:evaluation-claim",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    eval.refresh_from_db()
    assert eval.status == Evaluation.CLAIMED
    assert eval.started_at is not None
    assert (
        response.json()
        == ExternalEvaluationSerializer(
            eval, context={"request": response.wsgi_request}
        ).data
    )

    # claiming an already claimed evaluation should fail
    response = get_view_for_user(
        viewname="api:evaluation-claim",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "You can only claim pending evaluations." in str(response.json())


@pytest.mark.django_db
def test_evaluator_can_only_claim_one_eval_at_a_time(client):
    evaluation = create_claimable_evaluation()
    external_evaluator, challenge_admin, challenge_participant = (
        get_user_groups(evaluation)
    )
    _ = EvaluationFactory(
        status=Evaluation.CLAIMED,
        submission__phase=evaluation.submission.phase,
        method=None,
        claimed_by=external_evaluator,
    )
    response = get_view_for_user(
        viewname="api:evaluation-claim",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": evaluation.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "status": "You can only claim one evaluation at a time."
    }


@pytest.mark.usefixtures("client")
class TestUpdateExternalEvaluation(TestCase):
    def setUp(self):
        self.claimed_evaluation = create_claimable_evaluation()
        (
            self.external_evaluator,
            self.challenge_admin,
            self.challenge_participant,
        ) = get_user_groups(self.claimed_evaluation)
        self.unclaimed_evaluation = EvaluationFactory(
            submission__algorithm_image=self.claimed_evaluation.submission.algorithm_image,
            submission__phase=self.claimed_evaluation.submission.phase,
            method=None,
        )
        _ = get_view_for_user(
            viewname="api:evaluation-claim",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            content_type="application/json",
        )
        self.claimed_evaluation.refresh_from_db()

    @pytest.mark.django_db
    def test_update_external_evaluation_permissions(self):
        for user in [self.challenge_admin, self.challenge_participant]:
            response = get_view_for_user(
                viewname="api:evaluation-update-external-evaluation",
                client=self.client,
                method=self.client.patch,
                user=user,
                reverse_kwargs={"pk": self.claimed_evaluation.pk},
                content_type="application/json",
            )
            assert response.status_code == 403
            assert "You do not have permission to perform this action." in str(
                response.json()
            )

        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            content_type="application/json",
            data={
                "status": "Failed",
                "error_message": "Error message",
            },
        )
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_evaluation_needs_to_be_claimed_before_update(self):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.unclaimed_evaluation.pk},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert (
            "You need to claim an evaluation before you can update it."
            in str(response.json())
        )

    @pytest.mark.django_db
    def test_update_failed_evaluation_without_error_message(self):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={
                "status": "Failed",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "An error_message is required for failed evaluations." in str(
            response.json()
        )

    @pytest.mark.django_db
    def test_update_failed_external_evaluation(self):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={
                "status": "Failed",
                "error_message": "Error message",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        self.claimed_evaluation.refresh_from_db()
        assert self.claimed_evaluation.status == Evaluation.FAILURE
        assert self.claimed_evaluation.completed_at is not None
        assert self.claimed_evaluation.compute_cost_euro_millicents == 0
        assert self.claimed_evaluation.outputs.count() == 0

    @pytest.mark.django_db
    def test_updated_successful_evaluation_without_metrics(self):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={
                "status": "Succeeded",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "Metrics are required for successful evaluations." in str(
            response.json()
        )

    @pytest.mark.django_db
    def test_update_successful_external_evaluation(self):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 200
        self.claimed_evaluation.refresh_from_db()
        assert self.claimed_evaluation.status == Evaluation.SUCCESS
        assert self.claimed_evaluation.completed_at is not None
        assert self.claimed_evaluation.compute_cost_euro_millicents == 0
        assert self.claimed_evaluation.outputs.count() == 1
        assert response.json() == {
            "metrics": "foo-bar",
            "status": "Succeeded",
            "error_message": "",
        }

    @override_settings(
        EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS=0,
        task_eager_propagates=True,
        task_always_eager=True,
    )
    @pytest.mark.django_db
    def test_timeout(self):
        time.sleep(1)
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=self.external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {
            "status": "You can only update an evaluation within 24 hours."
        }
        self.claimed_evaluation.refresh_from_db()
        assert self.claimed_evaluation.status == Evaluation.CANCELLED
        assert self.claimed_evaluation.compute_cost_euro_millicents == 0
        assert (
            self.claimed_evaluation.error_message
            == "External evaluation timed out."
        )

    @pytest.mark.django_db
    def test_claim_evaluation_by_different_evaluator(self):
        another_external_evaluator = UserFactory()
        self.claimed_evaluation.submission.phase.challenge.external_evaluators_group.user_set.add(
            another_external_evaluator
        )
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=self.client,
            method=self.client.patch,
            user=another_external_evaluator,
            reverse_kwargs={"pk": self.claimed_evaluation.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert response.json() == {
            "status": "You do not have permission to update this evaluation."
        }
