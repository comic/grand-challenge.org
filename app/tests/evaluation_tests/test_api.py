import time
from datetime import timedelta
from typing import NamedTuple

import pytest

from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.serializers import (
    ExternalEvaluationSerializer,
    FilteredMetricsJsonSerializer,
)
from grandchallenge.evaluation.utils import Metric, SubmissionKindChoices
from grandchallenge.notifications.models import Notification
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
    AlgorithmInterfaceFactory,
)
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


class ExternalEvaluationSet(NamedTuple):
    evaluation: EvaluationFactory
    admin: UserFactory
    participant: UserFactory
    external_evaluator: UserFactory


def generate_claimable_evaluation():
    external_evaluator, admin, participant = UserFactory.create_batch(3)
    challenge = ChallengeFactory(creator=admin)
    challenge.add_admin(admin)
    challenge.add_participant(participant)
    challenge.external_evaluators_group.user_set.add(external_evaluator)

    p1, p2 = PhaseFactory.create_batch(
        2, challenge=challenge, submission_kind=SubmissionKindChoices.ALGORITHM
    )
    ci1, ci2 = ComponentInterfaceFactory.create_batch(2)
    interface = AlgorithmInterfaceFactory(inputs=[ci1], outputs=[ci2])
    for phase in [p1, p2]:
        phase.algorithm_interfaces.set([interface])
    p2.external_evaluation = True
    p2.parent = p1
    p2.save()
    ai = AlgorithmImageFactory(
        algorithm=AlgorithmFactory(),
        is_manifest_valid=True,
        is_in_registry=True,
        is_desired_version=True,
    )
    ai.algorithm.interfaces.set([interface])

    eval = EvaluationFactory(
        submission__algorithm_image=ai,
        submission__phase=p2,
        method=None,
        time_limit=60,
    )

    return ExternalEvaluationSet(
        evaluation=eval,
        admin=admin,
        participant=participant,
        external_evaluator=external_evaluator,
    )


@pytest.fixture
def claimable_external_evaluation():
    return generate_claimable_evaluation()


@pytest.fixture
def two_claimable_external_evaluations():
    return [generate_claimable_evaluation(), generate_claimable_evaluation()]


@pytest.fixture
def claimed_external_evaluation(client, claimable_external_evaluation):
    _ = get_view_for_user(
        viewname="api:evaluation-claim",
        client=client,
        method=client.patch,
        user=claimable_external_evaluation.external_evaluator,
        reverse_kwargs={"pk": claimable_external_evaluation.evaluation.pk},
        content_type="application/json",
    )
    claimable_external_evaluation.evaluation.refresh_from_db()
    return ExternalEvaluationSet(
        evaluation=claimable_external_evaluation.evaluation,
        admin=claimable_external_evaluation.admin,
        participant=claimable_external_evaluation.participant,
        external_evaluator=claimable_external_evaluation.external_evaluator,
    )


@pytest.mark.django_db
def test_claimable_evaluations(client, claimable_external_evaluation):
    e1 = claimable_external_evaluation.evaluation
    assert e1.status == Evaluation.PENDING

    EvaluationFactory(
        submission__phase=e1.submission.phase,
        submission__algorithm_image=e1.submission.algorithm_image,
        method=None,
        status=Evaluation.EXECUTING,
        time_limit=60,
    )
    EvaluationFactory(
        submission__phase=e1.submission.phase.parent, time_limit=10
    )

    for user in [
        claimable_external_evaluation.admin,
        claimable_external_evaluation.participant,
    ]:
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
        user=claimable_external_evaluation.external_evaluator,
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
def test_claim_evaluation(client, claimable_external_evaluation):
    eval = claimable_external_evaluation.evaluation

    for user in [
        claimable_external_evaluation.admin,
        claimable_external_evaluation.participant,
    ]:
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
        user=claimable_external_evaluation.external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    eval.refresh_from_db()
    assert eval.status == Evaluation.CLAIMED
    assert eval.claimed_at is not None
    assert eval.claimed_by == claimable_external_evaluation.external_evaluator
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
        user=claimable_external_evaluation.external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "You can only claim pending evaluations." in str(response.json())


@pytest.mark.django_db
def test_evaluator_can_only_claim_one_eval_at_a_time(
    client, claimable_external_evaluation
):
    _ = EvaluationFactory(
        status=Evaluation.CLAIMED,
        submission__phase=claimable_external_evaluation.evaluation.submission.phase,
        method=None,
        claimed_by=claimable_external_evaluation.external_evaluator,
        time_limit=60,
    )
    response = get_view_for_user(
        viewname="api:evaluation-claim",
        client=client,
        method=client.patch,
        user=claimable_external_evaluation.external_evaluator,
        reverse_kwargs={"pk": claimable_external_evaluation.evaluation.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "status": "You can only claim one evaluation at a time."
    }


@pytest.mark.django_db
class TestUpdateExternalEvaluation:
    def test_update_external_evaluation_permissions(
        self, client, claimed_external_evaluation
    ):
        for user in [
            claimed_external_evaluation.admin,
            claimed_external_evaluation.participant,
        ]:
            response = get_view_for_user(
                viewname="api:evaluation-update-external-evaluation",
                client=client,
                method=client.patch,
                user=user,
                reverse_kwargs={
                    "pk": claimed_external_evaluation.evaluation.pk
                },
                content_type="application/json",
            )
            assert response.status_code == 403
            assert "You do not have permission to perform this action." in str(
                response.json()
            )

        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_external_evaluation.evaluation.pk},
            content_type="application/json",
            data={
                "status": "Failed",
                "error_message": "Error message",
            },
        )
        assert response.status_code == 200

    def test_evaluation_needs_to_be_claimed_before_update(
        self, client, claimed_external_evaluation
    ):
        unclaimed_evaluation = EvaluationFactory(
            submission__algorithm_image=claimed_external_evaluation.evaluation.submission.algorithm_image,
            submission__phase=claimed_external_evaluation.evaluation.submission.phase,
            method=None,
            time_limit=60,
        )
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": unclaimed_evaluation.pk},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert (
            "You need to claim an evaluation before you can update it."
            in str(response.json())
        )

    def test_update_failed_evaluation_without_error_message(
        self, client, claimed_external_evaluation
    ):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_external_evaluation.evaluation.pk},
            data={
                "status": "Failed",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "An error_message is required for failed evaluations." in str(
            response.json()
        )

    def test_update_failed_external_evaluation(
        self, client, claimed_external_evaluation
    ):
        # reset notifications
        Notification.objects.all().delete()
        claimed_eval = claimed_external_evaluation.evaluation
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_eval.pk},
            data={
                "status": "Failed",
                "error_message": "Error message",
            },
            content_type="application/json",
        )
        assert response.status_code == 200

        claimed_eval.refresh_from_db()
        assert claimed_eval.status == Evaluation.FAILURE
        assert claimed_eval.evaluation_utilization.duration is not None
        assert (
            claimed_eval.evaluation_utilization.compute_cost_euro_millicents
            == 0
        )
        assert claimed_eval.outputs.count() == 0

        # notifications sent to challenge admin and submission creator
        assert Notification.objects.count() == 2
        recipients = [
            notification.user for notification in Notification.objects.all()
        ]
        assert set(recipients) == {
            claimed_external_evaluation.admin,
            claimed_eval.submission.creator,
        }

    def test_updated_successful_evaluation_without_metrics(
        self, client, claimed_external_evaluation
    ):
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_external_evaluation.evaluation.pk},
            data={
                "status": "Succeeded",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "Metrics are required for successful evaluations." in str(
            response.json()
        )

    def test_update_successful_external_evaluation(
        self, client, claimed_external_evaluation
    ):
        # reset notifications
        Notification.objects.all().delete()
        claimed_eval = claimed_external_evaluation.evaluation
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_eval.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 200
        claimed_eval.refresh_from_db()
        assert claimed_eval.status == Evaluation.SUCCESS
        assert claimed_eval.evaluation_utilization.duration is not None
        assert (
            claimed_eval.evaluation_utilization.compute_cost_euro_millicents
            == 0
        )
        assert claimed_eval.outputs.count() == 1
        assert response.json() == {
            "metrics": "foo-bar",
            "status": "Succeeded",
            "error_message": "",
        }
        # notifications sent to challenge admin and submission creator
        assert Notification.objects.count() == 2
        recipients = [
            notification.user for notification in Notification.objects.all()
        ]
        assert set(recipients) == {
            claimed_external_evaluation.admin,
            claimed_eval.submission.creator,
        }

    def test_timeout(self, client, settings, claimed_external_evaluation):
        settings.EXTERNAL_EVALUATION_TIMEOUT_IN_SECONDS = 0
        settings.task_eager_propagates = (True,)
        settings.task_always_eager = (True,)

        time.sleep(1)
        # reset notifications
        Notification.objects.all().delete()

        claimed_eval = claimed_external_evaluation.evaluation

        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=claimed_external_evaluation.external_evaluator,
            reverse_kwargs={"pk": claimed_eval.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert response.json() == {
            "status": "The evaluation was not updated in time."
        }
        claimed_eval.refresh_from_db()
        assert claimed_eval.status == Evaluation.CANCELLED
        assert (
            claimed_eval.evaluation_utilization.compute_cost_euro_millicents
            == 0
        )
        assert claimed_eval.error_message == "External evaluation timed out."

        assert Notification.objects.count() == 2
        receivers = [
            notification.user for notification in Notification.objects.all()
        ]
        assert claimed_external_evaluation.admin in receivers
        assert claimed_eval.submission.creator in receivers
        assert claimed_external_evaluation.participant not in receivers
        assert claimed_external_evaluation.external_evaluator not in receivers

    def test_claim_evaluation_by_different_evaluator(
        self, client, claimed_external_evaluation
    ):
        another_external_evaluator = UserFactory()
        claimed_external_evaluation.evaluation.submission.phase.challenge.external_evaluators_group.user_set.add(
            another_external_evaluator
        )
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
            client=client,
            method=client.patch,
            user=another_external_evaluator,
            reverse_kwargs={"pk": claimed_external_evaluation.evaluation.pk},
            data={"metrics": "foo-bar", "status": "Succeeded"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert response.json() == {
            "status": "You do not have permission to update this evaluation."
        }


@pytest.mark.django_db
def test_claimable_evaluations_filter(
    client, two_claimable_external_evaluations
):
    e1 = two_claimable_external_evaluations[0].evaluation
    e2 = two_claimable_external_evaluations[1].evaluation
    external_evaluator = two_claimable_external_evaluations[
        0
    ].external_evaluator
    assert e1.status == Evaluation.PENDING
    assert e2.status == Evaluation.PENDING

    e2.submission.phase.challenge.external_evaluators_group.user_set.add(
        external_evaluator
    )

    response = get_view_for_user(
        viewname="api:evaluation-claimable-evaluations",
        client=client,
        user=external_evaluator,
        content_type="application/json",
    )
    assert response.status_code == 200
    # both are claimable
    assert {e["pk"] for e in response.json()} == {str(e1.pk), str(e2.pk)}

    # filter by phase
    response = get_view_for_user(
        viewname="api:evaluation-claimable-evaluations",
        client=client,
        user=external_evaluator,
        content_type="application/json",
        data={"submission__phase": e1.submission.phase.pk},
    )
    assert response.status_code == 200
    # only e1 is returned
    assert {e["pk"] for e in response.json()} == {str(e1.pk)}


@pytest.mark.django_db
def test_metrics_json_filtering():
    interface = ComponentInterface.objects.get(slug="metrics-json-file")
    civ = ComponentInterfaceValueFactory(
        value={
            "l1": {"l2": {"l3a": 1, "l3b": 2}, "l2a": 3},
            "l1v": "Sensitive",
            "l1d": {},
        },
        interface=interface,
    )
    test_metrics = [
        Metric(path="l1.l2.l3a", reverse=False),
        Metric(path="l1.l2.l3b", reverse=False),
        Metric(path="l1.l2a", reverse=False),
        Metric(path="l1d", reverse=False),
    ]

    assert (
        FilteredMetricsJsonSerializer(
            instance=civ, filter_metrics_json=False, valid_metrics=[]
        ).data["value"]
        == civ.value
    )
    assert (
        FilteredMetricsJsonSerializer(
            instance=civ, filter_metrics_json=True, valid_metrics=[]
        ).data["value"]
        == {}
    )
    assert FilteredMetricsJsonSerializer(
        instance=civ, filter_metrics_json=True, valid_metrics=test_metrics
    ).data["value"] == {"l1": {"l2": {"l3a": 1, "l3b": 2}, "l2a": 3}}

    civ.interface = ComponentInterfaceFactory()
    civ.save()

    # Non metrics-json interfaces should not be filtered
    assert (
        FilteredMetricsJsonSerializer(
            instance=civ, filter_metrics_json=True, valid_metrics=test_metrics
        ).data["value"]
        == civ.value
    )


@pytest.mark.django_db
def test_evaluation_metrics_filtering(client):
    user = UserFactory()

    # Ensure object based filtering is used
    other_challenge = ChallengeFactory()
    other_challenge.add_admin(user=user)

    phase = PhaseFactory(
        challenge__hidden=False,
        display_all_metrics=False,
        public=True,
        score_jsonpath="l1.l2a",
        score_title="Whatevs",
    )
    full_value = {
        "l1": {"l2": {"l3a": 1, "l3b": 2}, "l2a": 3},
        "l1v": "Sensitive",
        "l1d": {},
    }
    filtered_value = {"l1": {"l2a": 3}}

    ci = ComponentInterface.objects.get(slug="metrics-json-file")
    civ = ComponentInterfaceValueFactory(interface=ci, value=full_value)
    evaluation = EvaluationFactory(
        submission__phase=phase,
        time_limit=phase.evaluation_time_limit,
        published=True,
    )
    evaluation.outputs.set([civ])

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="api:evaluation-detail",
        reverse_kwargs={"pk": evaluation.pk},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["outputs"][0]["value"] == filtered_value

    phase.challenge.add_admin(user=user)

    response = get_view_for_user(
        client=client,
        user=user,
        viewname="api:evaluation-detail",
        reverse_kwargs={"pk": evaluation.pk},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["outputs"][0]["value"] == full_value

    phase.display_all_metrics = True
    phase.save()

    response = get_view_for_user(
        client=client,
        viewname="api:evaluation-detail",
        reverse_kwargs={"pk": evaluation.pk},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["outputs"][0]["value"] == full_value


@pytest.mark.django_db
def test_durations_are_serialized(client):
    user = UserFactory()
    evaluation = EvaluationFactory(
        time_limit=60,
        exec_duration=timedelta(seconds=1337),
        invoke_duration=timedelta(seconds=1874),
    )
    evaluation.submission.phase.challenge.add_admin(user=user)

    response = get_view_for_user(
        client=client, url=evaluation.api_url, user=user
    ).json()

    assert response["exec_duration"] == "P0DT00H22M17S"
    assert response["invoke_duration"] == "P0DT00H31M14S"
