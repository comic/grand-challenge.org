import pytest
from actstream.actions import is_following
from actstream.models import Action
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from machina.apps.forum_conversation.models import Topic

from grandchallenge.challenges.models import Challenge
from grandchallenge.notifications.models import Notification
from tests.evaluation_tests.factories import PhaseFactory, SubmissionFactory
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
def test_default_page_is_created():
    c = ChallengeFactory()
    assert c.page_set.count() == 1


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

    # No actions involving the forum should be created
    for i in Action.objects.all():
        assert c.forum != i.target
        assert c.forum != i.action_object
        assert c.forum != i.actor


@pytest.mark.django_db
@pytest.mark.parametrize("group", ("participant", "admin"))
def test_non_posters_notified(group):
    p = UserFactory()
    u = UserFactory()
    c = ChallengeFactory()
    c.add_admin(user=p)

    add_method = getattr(c, f"add_{group}")
    add_method(user=u)

    # delete all notifications for easier testing below
    Notification.objects.all().delete()

    TopicFactory(forum=c.forum, poster=p, type=Topic.TOPIC_ANNOUNCE)

    assert u.user_profile.has_unread_notifications is True
    assert p.user_profile.has_unread_notifications is False


@pytest.mark.django_db
def test_submission_limit_status():
    p1, p2, p3, p4 = PhaseFactory.create_batch(
        4, total_number_of_submissions_allowed=10
    )
    p5 = PhaseFactory()
    SubmissionFactory.create_batch(10, phase=p1)
    SubmissionFactory.create_batch(4, phase=p2)
    SubmissionFactory.create_batch(8, phase=p3)
    SubmissionFactory.create_batch(12, phase=p4)

    assert p1.percent_of_total_submissions_allowed == 100
    assert p2.percent_of_total_submissions_allowed == 40
    assert p3.percent_of_total_submissions_allowed == 80
    assert p4.percent_of_total_submissions_allowed == 120
    assert not p5.percent_of_total_submissions_allowed

    assert p1.exceeds_total_number_of_submissions_allowed
    assert p4.exceeds_total_number_of_submissions_allowed
    for phase in [p2, p3, p5]:
        assert not phase.exceeds_total_number_of_submissions_allowed

    for ch in [p1.challenge, p2.challenge, p3.challenge, p4.challenge]:
        assert ch.total_number_of_submissions_defined
    assert not p5.challenge.total_number_of_submissions_defined

    assert p1.challenge.exceeds_total_number_of_submissions_allowed
    assert p4.challenge.exceeds_total_number_of_submissions_allowed
    for ch in [p2.challenge, p3.challenge, p5.challenge]:
        assert not ch.exceeds_total_number_of_submissions_allowed

    for ch in [p1.challenge, p3.challenge, p4.challenge]:
        assert ch.exceeds_70_percent_of_submission_allowed
    assert not p2.challenge.exceeds_70_percent_of_submission_allowed
    assert not p5.challenge.exceeds_70_percent_of_submission_allowed
