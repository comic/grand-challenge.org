from django.contrib.auth.models import Group
from django.test.testcases import TestCase

from comic.eyra.models import Algorithm
from tests.factories import AlgorithmFactory, UserFactory


class AlgorithmDeleteTest(TestCase):
    def test_delete_admin_group_with_algorithm(self):
        user = UserFactory()
        algorithm: Algorithm = AlgorithmFactory(
            creator=user
        )

        algorithm_pk = algorithm.pk
        admin_group_pk = algorithm.admin_group.pk

        algorithm.delete()

        # algorithm does not exist
        with self.assertRaises(Algorithm.DoesNotExist):
            Algorithm.objects.get(pk=algorithm_pk)

        # admin group does not exist
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=admin_group_pk)

    def test_queryset_delete_admin_group_with_algorithm(self):
        user = UserFactory()
        algorithm: Algorithm = AlgorithmFactory(
            creator=user
        )

        algorithm_pk = algorithm.pk
        admin_group_pk = algorithm.admin_group.pk

        Algorithm.objects.filter(pk=algorithm_pk).delete()

        # algorithm does not exist
        with self.assertRaises(Algorithm.DoesNotExist):
            Algorithm.objects.get(pk=algorithm_pk)

        # admin group does not exist
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=admin_group_pk)