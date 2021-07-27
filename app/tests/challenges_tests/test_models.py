import pytest
from actstream.actions import is_following
from actstream.models import Action
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.db.models import ProtectedError
from machina.apps.forum_conversation.models import Topic

from grandchallenge.challenges.models import Challenge
from grandchallenge.notifications.models import Notification
from tests.factories import ChallengeFactory, UserFactory
from tests.notifications_tests.factories import TopicFactory


@pytest.mark.django_db
def test_group_deletion():
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    challenge.page_set.all().delete()
    challenge.phase_set.all().delete()
    Challenge.objects.filter(pk__in=[challenge.pk]).delete()

    with pytest.raises(ObjectDoesNotExist):
        participants_group.refresh_from_db()

    with pytest.raises(ObjectDoesNotExist):
        admins_group.refresh_from_db()


@pytest.mark.django_db
@pytest.mark.parametrize("group", ["participants_group", "admins_group"])
def test_group_deletion_reverse(group):
    challenge = ChallengeFactory()
    participants_group = challenge.participants_group
    admins_group = challenge.admins_group

    assert participants_group
    assert admins_group

    with pytest.raises(ProtectedError):
        getattr(challenge, group).delete()


@pytest.mark.django_db
def test_default_pages_are_created():
    c = ChallengeFactory()
    assert c.page_set.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("group", ("participant", "admin"))
def test_participants_follow_forum(group):
    u = UserFactory()
    c = ChallengeFactory()

    add_method = getattr(c, f"add_{group}")
    remove_method = getattr(c, f"remove_{group}")

    add_method(user=u)
    assert is_following(user=u, obj=c.forum)

    remove_method(user=u)
    assert is_following(user=u, obj=c.forum) is False

    # Only one action (challenge creation) should be created
    assert Action.objects.count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize("group", ("participant", "admin"))
def test_non_posters_notified(group):
    p = UserFactory()
    u = UserFactory()
    c = ChallengeFactory()

    c.add_admin(user=p)

    add_method = getattr(c, f"add_{group}")
    add_method(user=u)

    TopicFactory(forum=c.forum, poster=p, type=Topic.TOPIC_ANNOUNCE)

    assert u.user_profile.has_unread_notifications is True
    assert p.user_profile.has_unread_notifications is False


@pytest.mark.django_db
def test_staff_users_notified_of_challenge_creation():
    staff_user = UserFactory(is_staff=True)
    call_command("create_staff_follows")
    assert is_following(staff_user, Site.objects.get_current())

    challenge = ChallengeFactory()
    assert len(Notification.objects.all()) == 1
    assert Notification.objects.first().user == staff_user
    assert (
        f"created the challenge {challenge.short_name} on {Site.objects.get_current()}"
        in str(Notification.objects.first().action)
    )
