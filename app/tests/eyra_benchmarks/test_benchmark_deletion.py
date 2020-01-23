from django.contrib.auth.models import Group
from django.test.testcases import TestCase

from comic.eyra.models import Benchmark
from tests.factories import BenchmarkFactory, UserFactory


class BenchmarkDeleteTest(TestCase):
    def test_delete_admin_group_with_benchmark(self):
        user = UserFactory()
        benchmark: Benchmark = BenchmarkFactory(
            creator=user
        )

        benchmark_pk = benchmark.pk
        admin_group_pk = benchmark.admin_group.pk

        benchmark.delete()

        # benchmark does not exist
        with self.assertRaises(Benchmark.DoesNotExist):
            Benchmark.objects.get(pk=benchmark_pk)

        # admin group does not exist
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=admin_group_pk)

    def test_queryset_delete_admin_group_with_benchmark(self):
        user = UserFactory()
        benchmark: Benchmark = BenchmarkFactory(
            creator=user
        )

        benchmark_pk = benchmark.pk
        admin_group_pk = benchmark.admin_group.pk

        Benchmark.objects.filter(pk=benchmark_pk).delete()

        # benchmark does not exist
        with self.assertRaises(Benchmark.DoesNotExist):
            Benchmark.objects.get(pk=benchmark_pk)

        # admin group does not exist
        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=admin_group_pk)
