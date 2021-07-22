import pytest

from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKind,
)
from grandchallenge.evaluation.models import Evaluation
from tests.evaluation_tests.factories import EvaluationFactory, PhaseFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_setting_submission_page_html(client, challenge_set):
    custom_html = "<p>My custom html</p>"

    response = get_view_for_user(
        client=client,
        user=challenge_set.participant,
        viewname="evaluation:submission-create",
        reverse_kwargs={
            "challenge_short_name": challenge_set.challenge.short_name,
            "slug": challenge_set.challenge.phase_set.get().slug,
        },
    )

    assert response.status_code == 200
    assert custom_html not in response.rendered_content

    phase = challenge_set.challenge.phase_set.get()
    phase.submission_page_html = custom_html
    phase.save()

    response = get_view_for_user(
        client=client,
        user=challenge_set.participant,
        viewname="evaluation:submission-create",
        reverse_kwargs={
            "challenge_short_name": challenge_set.challenge.short_name,
            "slug": challenge_set.challenge.phase_set.get().slug,
        },
    )

    assert response.status_code == 200
    assert custom_html in response.rendered_content


@pytest.mark.django_db
def test_setting_display_all_metrics(client, challenge_set):
    metrics = {"public": 3245.235, "secret": 4328.432, "extra": 2144.312}
    phase = challenge_set.challenge.phase_set.get()

    e = EvaluationFactory(submission__phase=phase, status=Evaluation.SUCCESS)

    e.outputs.add(
        ComponentInterfaceValue.objects.create(
            interface=ComponentInterface.objects.get(slug="metrics-json-file"),
            value=metrics,
        )
    )

    phase.score_jsonpath = "public"
    phase.extra_results_columns = [
        {"title": "extra", "path": "extra", "order": "asc"}
    ]
    phase.display_all_metrics = True
    phase.save()

    response = get_view_for_user(
        client=client,
        viewname="evaluation:detail",
        challenge=challenge_set.challenge,
        reverse_kwargs={"pk": e.pk},
        user=challenge_set.challenge.creator,
    )

    assert response.status_code == 200
    assert str(metrics["public"]) in response.rendered_content
    assert str(metrics["extra"]) in response.rendered_content
    assert str(metrics["secret"]) in response.rendered_content

    phase.display_all_metrics = False
    phase.save()

    response = get_view_for_user(
        client=client,
        viewname="evaluation:detail",
        challenge=challenge_set.challenge,
        reverse_kwargs={"pk": e.pk},
        user=challenge_set.challenge.creator,
    )

    assert response.status_code == 200
    assert str(metrics["public"]) in response.rendered_content
    assert str(metrics["extra"]) in response.rendered_content
    assert str(metrics["secret"]) not in response.rendered_content


@pytest.mark.django_db
def test_default_interfaces_created():
    p = PhaseFactory()

    assert {i.kind for i in p.inputs.all()} == {
        InterfaceKind.InterfaceKindChoices.CSV
    }
    assert {o.kind for o in p.outputs.all()} == {
        InterfaceKind.InterfaceKindChoices.ANY
    }
