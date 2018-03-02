import pytest

from comicmodels.models import Page
from tests.factories import PageFactory
from tests.utils import (
    validate_admin_only_view,
    get_view_for_user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'pages:list',
        'pages:create',
    ]
)
def test_page_admin_permissions(view, client, TwoChallengeSets):
    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client
    )


@pytest.mark.django_db
def test_page_update_permissions(client, TwoChallengeSets):
    p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                     title='challenge1page1permissiontest')

    validate_admin_only_view(
        viewname='pages:update',
        two_challenge_set=TwoChallengeSets,
        client=client,
        reverse_kwargs={'page_title': p1.title},
    )


@pytest.mark.django_db
def test_page_list_filter(client, TwoChallengeSets):
    """ Check that only pages related to this challenge are listed """
    p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                     title='challenge1page1')
    p2 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet2.challenge,
                     title='challenge2page1')

    response = get_view_for_user(
        viewname='pages:list',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12)

    assert p1.title in response.rendered_content
    assert p2.title not in response.rendered_content

    response = get_view_for_user(
        viewname='pages:list',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        user=TwoChallengeSets.admin12
    )

    assert p1.title not in response.rendered_content
    assert p2.title in response.rendered_content


@pytest.mark.django_db
def test_page_create(client, TwoChallengeSets):
    page_html = '<h1>HELLO WORLD</h1>'
    page_title = 'testpage1'

    response = get_view_for_user(
        viewname='pages:create',
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.ChallengeSet1.admin,
        data={
            'title': page_title,
            'html': page_html,
            'permission_lvl': Page.ALL,
        }
    )

    assert response.status_code == 302

    response = get_view_for_user(
        url=response.url,
        client=client,
        method=client.get,
    )

    assert response.status_code == 200
    assert page_html in str(response.content)

    # Check that it was created in the correct challenge
    response = get_view_for_user(
        viewname='pages:detail',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        reverse_kwargs={'page_title': page_title}
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname='pages:detail',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        reverse_kwargs={'page_title': page_title}
    )

    assert response.status_code == 404

@pytest.mark.django_db
def test_page_update(client, ChallengeSet):
    p1 = PageFactory(comicsite=ChallengeSet.challenge,
                     title='challenge1page1updatetest',
                     html='oldhtml')

    response = get_view_for_user(
        viewname='pages:update',
        client=client,
        method=client.get,
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={'page_title': p1.title}
    )

    assert response.status_code == 200
    assert 'value=\"challenge1page1updatetest\"' in response.rendered_content

    response = get_view_for_user(
        viewname='pages:update',
        client=client,
        method=client.post,
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={'page_title': p1.title},
        data={
            'title': 'editedtitle',
            'permission_lvl': Page.ALL,
            'html': 'newhtml',
        }
    )

    assert response.status_code == 302

    response = get_view_for_user(
        viewname='pages:detail',
        client=client,
        method=client.get,
        challenge=ChallengeSet.challenge,
        user=ChallengeSet.admin,
        reverse_kwargs={'page_title': 'editedtitle'},
    )

    assert response.status_code == 200
    assert 'newhtml' in str(response.content)
