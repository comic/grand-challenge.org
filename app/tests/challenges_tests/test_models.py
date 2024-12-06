import random

import pytest
from actstream.actions import is_following
from actstream.models import Action
from dateutil.relativedelta import relativedelta
from dateutil.utils import today
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from machina.apps.forum_conversation.models import Topic

from grandchallenge.challenges.models import Challenge
from grandchallenge.notifications.models import Notification
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    UserFactory,
)
from tests.notifications_tests.factories import TopicFactory
from tests.organizations_tests.factories import OrganizationFactory


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
def test_is_active_until_set():
    c = ChallengeFactory()
    assert c.is_active_until == today().date() + relativedelta(months=12)


@pytest.mark.django_db
def test_total_challenge_cost(settings):
    settings.COMPONENTS_DEFAULT_BACKEND = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"

    user_exempt_from_base_cost, normal_user = UserFactory.create_batch(2)
    request1 = ChallengeRequestFactory(
        creator=user_exempt_from_base_cost, expected_number_of_teams=3
    )
    request2 = ChallengeRequestFactory(
        creator=normal_user, expected_number_of_teams=3
    )
    request3 = ChallengeRequestFactory(
        creator=normal_user, expected_number_of_teams=10
    )
    request4 = ChallengeRequestFactory(
        creator=normal_user,
        expected_number_of_teams=10,
        algorithm_selectable_gpu_type_choices=["", "A10G", "T4"],
    )

    organisation = OrganizationFactory(exempt_from_base_costs=True)
    organisation.members_group.user_set.add(user_exempt_from_base_cost)

    assert request1.storage_and_compute_cost_surplus == -270
    assert request1.total_challenge_cost == 1000

    assert request2.storage_and_compute_cost_surplus == -270
    assert request2.total_challenge_cost == 6000

    assert request3.storage_and_compute_cost_surplus == 1380
    assert request3.total_challenge_cost == 7500

    assert request4.storage_and_compute_cost_surplus == 2580
    assert request4.total_challenge_cost == 9000


@pytest.mark.django_db
def test_storage_and_compute_cost_add_up_to_total():
    user = UserFactory()

    for _ in range(10):
        request = ChallengeRequestFactory(
            creator=user,
            expected_number_of_teams=random.randint(0, 50),
            inference_time_limit_in_minutes=random.randint(0, 50),
            average_size_of_test_image_in_mb=random.randint(0, 500),
            phase_1_number_of_submissions_per_team=random.randint(0, 50),
            phase_2_number_of_submissions_per_team=random.randint(0, 50),
            phase_1_number_of_test_images=random.randint(0, 50),
            phase_2_number_of_test_images=random.randint(0, 50),
        )
        assert (
            request.total_challenge_cost
            == request.base_cost_euros
            + request.total_storage_to_be_invoiced
            + request.total_compute_to_be_invoiced
        )
