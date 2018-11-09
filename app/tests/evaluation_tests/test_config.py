import pytest

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
