import pytest
from guardian.shortcuts import assign_perm

from grandchallenge.components.models import ComponentInterface
from grandchallenge.evaluation.models import Evaluation
from grandchallenge.evaluation.serializers import ExternalEvaluationSerializer
from grandchallenge.evaluation.utils import SubmissionKindChoices
from tests.algorithms_tests.factories import (
    AlgorithmFactory,
    AlgorithmImageFactory,
)
from tests.components_tests.factories import ComponentInterfaceFactory
from tests.evaluation_tests.factories import PhaseFactory, SubmissionFactory
from tests.factories import ChallengeFactory, ImageFactory, UserFactory
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

    s = SubmissionFactory(phase=p2, algorithm_image=ai)
    return Evaluation.objects.get(submission=s)


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

    s2 = SubmissionFactory(
        phase=e1.submission.phase,
        algorithm_image=e1.submission.algorithm_image,
    )
    e2 = Evaluation.objects.get(submission=s2)
    e2.status = Evaluation.EXECUTING
    e2.save()

    SubmissionFactory(phase=e1.submission.phase.parent)

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
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 200
    eval.refresh_from_db()
    assert eval.status == Evaluation.EXECUTING
    assert eval.claimed_at is not None
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
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "You can only claim pending evaluations." in str(response.json())


@pytest.mark.django_db
def test_update_external_evaluation(client):
    eval = create_claimable_evaluation()
    external_evaluator, challenge_admin, challenge_participant = (
        get_user_groups(eval)
    )

    for user in [challenge_admin, challenge_participant]:
        response = get_view_for_user(
            viewname="api:evaluation-update-external-evaluation",
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

    # claiming an eval that is not in executing state should fail
    response = get_view_for_user(
        viewname="api:evaluation-update-external-evaluation",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "You need to claim an evaluation before you can update it." in str(
        response.json()
    )

    eval.status = Evaluation.EXECUTING
    eval.save()

    # try posting a non-json output
    ci = ComponentInterfaceFactory(kind=ComponentInterface.Kind.IMAGE)
    im = ImageFactory()
    assign_perm("view_image", external_evaluator, im)
    response = get_view_for_user(
        viewname="api:evaluation-update-external-evaluation",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        data={"outputs": [{"interface": ci.slug, "image": im.api_url}]},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "Evaluation outputs can only be json data." in str(response.json())

    response = get_view_for_user(
        viewname="api:evaluation-update-external-evaluation",
        client=client,
        method=client.patch,
        user=external_evaluator,
        reverse_kwargs={"pk": eval.pk},
        data={
            "outputs": [{"interface": "metrics-json-file", "value": "foo-bar"}]
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    eval.refresh_from_db()
    assert eval.status == Evaluation.SUCCESS
    assert eval.completed_at is not None
    assert eval.outputs.count() == 1
    assert (
        response.json()
        == ExternalEvaluationSerializer(
            eval, context={"request": response.wsgi_request}
        ).data
    )
