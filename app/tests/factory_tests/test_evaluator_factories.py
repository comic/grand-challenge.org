from rest_framework.test import APITestCase

from tests.factories import AlgorithmFactory, EvaluationInterfaceFactory, BenchmarkFactory, ImplementationFactory


class EvaluatorFactoriesTest(APITestCase):
    def test_eval_factories(self):
        interface = EvaluationInterfaceFactory()
        eval_algorithm = AlgorithmFactory(interface=interface)
        evaluator = ImplementationFactory(algorithm=eval_algorithm)
        benchmark = BenchmarkFactory(evaluator=evaluator)
        benchmark.clean()
