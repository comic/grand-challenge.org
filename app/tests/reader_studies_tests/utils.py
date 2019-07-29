from django.conf import settings
from django.contrib.auth.models import Group

from tests.factories import UserFactory


def get_rs_creator():
    creator = UserFactory()
    g = Group.objects.get(name=settings.READER_STUDY_CREATORS_GROUP_NAME)
    g.user_set.add(creator)
    return creator
