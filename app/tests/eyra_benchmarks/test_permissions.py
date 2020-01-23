from rest_framework.test import APITestCase

from comic.eyra.models import Benchmark
from tests.factories import BenchmarkFactory, UserFactory


class BenchmarkAdminTest(APITestCase):
    def test_creator_permissions(self):
        user = UserFactory()
        benchmark: Benchmark = BenchmarkFactory(
            creator=user
        )
        # creator is user
        self.assertEquals(benchmark.creator, user)

        # admin group was made
        self.assertIsNotNone(benchmark.admin_group)

        # user is part of admin group
        self.assertTrue(benchmark.admin_group.user_set.filter(pk=user.pk).exists())

        # user can thus edit benchmark
        self.assertTrue(user.has_perm('change_benchmark', benchmark))

        # user can change the admin group
        self.assertTrue(user.has_perm('change_group', benchmark.admin_group))

        other_user = UserFactory()
        # other user has no permissions
        self.assertFalse(other_user.has_perm('change_benchmark', benchmark))
        self.assertFalse(other_user.has_perm('change_group', benchmark.admin_group))
