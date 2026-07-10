from tests.algorithms_tests.factories import AlgorithmFactory
from tests.factories import UserFactory


class TwoAlgorithms:
    def __init__(self):
        self.creator = UserFactory()
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
