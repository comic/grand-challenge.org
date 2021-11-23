import pytest
from actstream.actions import is_following
from actstream.models import Follow
from django.utils.html import format_html

from grandchallenge.notifications.models import Notification
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.profiles.templatetags.profiles import user_profile_link
from tests.factories import (
    ChallengeFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_request_create_post(client, two_challenge_sets):
    user = UserFactory()
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_1.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=user,
    )
    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_1.challenge
    ).exists()


@pytest.mark.django_db
def test_duplicate_registration_denied(client, two_challenge_sets):
    user = UserFactory()
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_1.challenge
    ).exists()
    rr = RegistrationRequestFactory(
        user=user, challenge=two_challenge_sets.challenge_set_1.challenge
    )
    assert RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_1.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        user=user,
    )
    assert response.status_code == 200
    assert rr.status_to_string() in response.rendered_content
    # Creating a request in another challenge should work
    assert not RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_2.challenge
    ).exists()
    response = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=two_challenge_sets.challenge_set_2.challenge,
        user=user,
    )
    assert response.status_code == 302
    assert RegistrationRequest.objects.filter(
        user=user, challenge=two_challenge_sets.challenge_set_2.challenge
    ).exists()


@pytest.mark.django_db
def test_participation_request_notification_flow(client):
    user = UserFactory()
    ch = ChallengeFactory()
    assert is_following(ch.creator, ch)
    # challenge creation results in notification for new admin
    # delete this notification for more transparent testing below
    Notification.objects.all().delete()

    # create permission request
    _ = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=ch,
        user=user,
    )
    assert RegistrationRequest.objects.count() == 1
    reg = RegistrationRequest.objects.get()
    # requester follows the request object
    assert is_following(user, reg)
    # when participation request review is disabled,
    # no notification for admin should be created, only for the user
    assert Notification.objects.count() == 1
    assert Notification.objects.get().user != ch.creator
    assert Notification.objects.get().user == user

    # change participation review to active
    ch.require_participant_review = True
    ch.save()
    Notification.objects.all().delete()

    # when registration request is deleted, Follow is deleted as well
    reg.delete()
    assert not Follow.objects.filter(object_id=reg.pk).all() == 0

    # create new permission request
    user2 = UserFactory()
    _ = get_view_for_user(
        viewname="participants:registration-create",
        client=client,
        method=client.post,
        challenge=ch,
        user=user2,
    )

    reg2 = RegistrationRequest.objects.last()
    assert is_following(user2, reg2)
    # when participant review is required, a new request results in a notification
    # for the admins of the challenge
    assert Notification.objects.count() == 1
    assert Notification.objects.get().user == ch.creator
    target_string = format_html(
        '<a href="{}">{}</a>', ch.get_absolute_url(), ch
    )
    assert f"{user_profile_link(user2)} requested access to {target_string}" in Notification.objects.get().print_notification(
        user=ch.creator
    )

    Notification.objects.all().delete()
    # accept permission request
    _ = get_view_for_user(
        client=client,
        user=ch.creator,
        viewname="participants:registration-update",
        reverse_kwargs={"pk": reg2.pk},
        challenge=ch,
        method=client.post,
        data={"status": reg2.ACCEPTED},
    )

    reg2.refresh_from_db()
    assert reg2.status == "ACPT"
    assert Notification.objects.count() == 1
    # upon request acceptance, the user gets notified
    assert Notification.objects.first().user == user2
    assert "was approved" in Notification.objects.first().print_notification(
        user=user2
    )
    Notification.objects.all().delete()

    # reject permission request
    _ = get_view_for_user(
        client=client,
        user=ch.creator,
        viewname="participants:registration-update",
        reverse_kwargs={"pk": reg2.pk},
        challenge=ch,
        method=client.post,
        data={"status": reg2.REJECTED},
    )

    reg2.refresh_from_db()
    assert reg2.status == "RJCT"
    # upon request rejection, the user gets notified
    assert Notification.objects.get().user == user2
    assert "was rejected" in Notification.objects.get().print_notification(
        user=user2
    )
