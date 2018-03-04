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
        'pages:delete',
    ]
)
def test_page_admin_permissions(view, client, TwoChallengeSets):
    if view == 'pages:delete':
        PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                    title='challenge1pagepermtest')
        reverse_kwargs = {'page_title': 'challenge1pagepermtest'}
    else:
        reverse_kwargs = None

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
        reverse_kwargs=reverse_kwargs,
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
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12
    )

    assert p1.title in response.rendered_content
    assert p2.title not in response.rendered_content

    response = get_view_for_user(
        viewname='pages:list',
        client=client,
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
    )

    assert response.status_code == 200
    assert page_html in str(response.content)

    # Check that it was created in the correct challenge
    response = get_view_for_user(
        viewname='pages:detail',
        client=client,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        reverse_kwargs={'page_title': page_title}
    )

    assert response.status_code == 200

    response = get_view_for_user(
        viewname='pages:detail',
        client=client,
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        reverse_kwargs={'page_title': page_title}
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_page_update(client, TwoChallengeSets):
    p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                     title='page1updatetest',
                     html='oldhtml')

    # page with the same name in another challenge to check selection
    PageFactory(comicsite=TwoChallengeSets.ChallengeSet2.challenge,
                title='page1updatetest')

    response = get_view_for_user(
        viewname='pages:update',
        client=client,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.ChallengeSet1.admin,
        reverse_kwargs={'page_title': p1.title}
    )

    assert response.status_code == 200
    assert 'value=\"page1updatetest\"' in response.rendered_content

    response = get_view_for_user(
        viewname='pages:update',
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.ChallengeSet1.admin,
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
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.ChallengeSet1.admin,
        reverse_kwargs={'page_title': 'editedtitle'},
    )

    assert response.status_code == 200
    assert 'newhtml' in str(response.content)


@pytest.mark.django_db
def test_page_delete(client, TwoChallengeSets):
    # Two pages with the same title, make sure the right one is deleted
    c1p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                       title='page1')
    c2p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet2.challenge,
                       title='page1')

    assert Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()

    response = get_view_for_user(
        viewname='pages:delete',
        client=client,
        method=client.post,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12,
        reverse_kwargs={'page_title': 'page1'},
    )

    assert response.status_code == 302

    assert not Page.objects.filter(pk=c1p1.pk).exists()
    assert Page.objects.filter(pk=c2p1.pk).exists()

    response = get_view_for_user(
        url=response.url,
        client=client,
        user=TwoChallengeSets.admin12,
    )

    assert response.status_code == 200


# TODO: Test page moving

# TODO: Remove the sortables on edit etc.
