from rest_framework.test import APITestCase

from comic.eyra.models import Algorithm
from tests.factories import AlgorithmFactory, UserFactory


class AlgorithmAdminTest(APITestCase):
    def test_creator_permissions(self):
        user = UserFactory()
        algorithm: Algorithm = AlgorithmFactory(
            creator=user
        )
        # creator is user
        self.assertEquals(algorithm.creator, user)

        # admin group was made
        self.assertIsNotNone(algorithm.admin_group)

        # user is part of admin group
        self.assertTrue(algorithm.admin_group.user_set.filter(pk=user.pk).exists())

        # user can thus edit algorithm
        self.assertTrue(user.has_perm('change_algorithm', algorithm))

        # user can change the admin group
        self.assertTrue(user.has_perm('change_group', algorithm.admin_group))

        other_user = UserFactory()
        # other user has no permissions
        self.assertFalse(other_user.has_perm('change_algorithm', algorithm))
        self.assertFalse(other_user.has_perm('change_group', algorithm.admin_group))

    def test_default_user_permissions(self):
        user = UserFactory()
        self.assertTrue(user.has_perm('eyra.add_algorithm'))
        self.assertTrue(user.has_perm('eyra.add_submission'))
