from django.conf import settings
from django.contrib.auth.models import Group

from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory


def get_algorithm_creator():
    creator = UserFactory()
    g = Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
    g.user_set.add(creator)
    return creator


class TwoAlgorithms:
    def __init__(self):
        self.creator = get_algorithm_creator()
        self.alg1, self.alg2 = AlgorithmFactory(), AlgorithmFactory()
        self.editor1, self.user1, self.editor2, self.user2 = (
            UserFactory(),
            UserFactory(),
            UserFactory(),
            UserFactory(),
        )
        self.alg1.add_editor(user=self.editor1)
        self.alg2.add_editor(user=self.editor2)
        self.alg1.add_user(user=self.user1)
        self.alg2.add_user(user=self.user2)
        self.u = UserFactory()
