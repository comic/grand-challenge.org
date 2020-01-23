from rest_framework.test import APITestCase

from tests.factories import BenchmarkFactory


class BenchmarkFactoriesTest(APITestCase):
    def test_eval_factories(self):
        # eval_algorithm = AlgorithmFactory()
        benchmark = BenchmarkFactory()
        benchmark.clean()
