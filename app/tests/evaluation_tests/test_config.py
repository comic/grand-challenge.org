import pytest

from tests.factories import ResultFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_setting_submission_page_html(client, ChallengeSet):
    custom_html = "<p>My custom html</p>"

    response = get_view_for_user(
        client=client,
        user=ChallengeSet.participant,
        viewname="evaluation:submission-create",
        challenge=ChallengeSet.challenge,
    )

    assert response.status_code == 200
    assert custom_html not in response.rendered_content

    ChallengeSet.challenge.evaluation_config.submission_page_html = custom_html
    ChallengeSet.challenge.evaluation_config.save()

    response = get_view_for_user(
        client=client,
        user=ChallengeSet.participant,
        viewname="evaluation:submission-create",
        challenge=ChallengeSet.challenge,
    )

    assert response.status_code == 200
    assert custom_html in response.rendered_content


@pytest.mark.django_db
def test_setting_display_all_metrics(client, ChallengeSet):
    metrics = {"public": 3245.235, "secret": 4328.432, "extra": 2144.312}
    r = ResultFactory(
        metrics=metrics, job__submission__challenge=ChallengeSet.challenge
    )

    ChallengeSet.challenge.evaluation_config.score_jsonpath = "public"
    ChallengeSet.challenge.evaluation_config.extra_results_columns = [
        {"title": "extra", "path": "extra", "order": "asc"}
    ]
    ChallengeSet.challenge.evaluation_config.display_all_metrics = True
    ChallengeSet.challenge.evaluation_config.save()

    response = get_view_for_user(
        client=client,
        viewname="evaluation:result-detail",
        challenge=ChallengeSet.challenge,
        reverse_kwargs={"pk": r.pk},
    )

    assert response.status_code == 200
    assert str(metrics["public"]) in response.rendered_content
    assert str(metrics["extra"]) in response.rendered_content
    assert str(metrics["secret"]) in response.rendered_content

    ChallengeSet.challenge.evaluation_config.display_all_metrics = False
    ChallengeSet.challenge.evaluation_config.save()

    response = get_view_for_user(
        client=client,
        viewname="evaluation:result-detail",
        challenge=ChallengeSet.challenge,
        reverse_kwargs={"pk": r.pk},
    )

    assert response.status_code == 200
    assert str(metrics["public"]) in response.rendered_content
    assert str(metrics["extra"]) in response.rendered_content
    assert str(metrics["secret"]) not in response.rendered_content
