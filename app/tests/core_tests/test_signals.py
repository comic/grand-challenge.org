import pytest
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.contrib.auth.models import Group
from machina.apps.forum.models import Forum

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.archives_tests.factories import ArchiveFactory
from tests.factories import UserFactory
from tests.notifications_tests.factories import ForumFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "factory,reverse",
    (
        (AlgorithmFactory, True,),
        (ReaderStudyFactory, True,),
        (ArchiveFactory, True,),
        (AlgorithmFactory, False),
        (ReaderStudyFactory, False,),
        (ArchiveFactory, False,),
    ),
)
def test_update_editor_follows_signal(client, factory, reverse):
    m1, m2 = factory.create_batch(2)
    u1, u2, u3, u4 = UserFactory.create_batch(4)

    if not reverse:
        for user in [u1, u2, u3, u4]:
            user.groups.add(m1.editors_group, m2.editors_group)
        for user in [u3, u4]:
            user.groups.remove(m1.editors_group)
        for user in [u1, u2, u3, u4]:
            user.groups.remove(m2.editors_group)

    else:
        g = Group.objects.filter(name=m1.editors_group).get()
        g.user_set.add(u1, u2, u3, u4)
        g.user_set.remove(u3, u4)

    assert is_following(u1, m1)
    assert is_following(u2, m1)
    assert not is_following(u3, m1)
    assert not is_following(u4, m1)
    assert not is_following(u1, m2)
    assert not is_following(u2, m2)
    assert not is_following(u3, m2)
    assert not is_following(u4, m2)

    # Test clearing
    if reverse:
        u1.groups.clear()
    else:
        g = Group.objects.filter(name=m1.editors_group).get()
        g.user_set.clear()

    assert not is_following(u1, m1)


@pytest.mark.django_db
def test_user_follow_clean_up(client):
    user = UserFactory()
    # create a forum that the user follows
    f = ForumFactory(type=Forum.FORUM_POST)
    follow(user, f)
    assert Follow.objects.count() == 1

    # delete user and check that follow is deleted as well
    user.delete()
    assert Follow.objects.count() == 0
