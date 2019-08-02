from rest_framework.test import APITestCase

from comic.eyra_algorithms.models import Algorithm
from tests.factories import AlgorithmFactory, UserFactory, InterfaceFactory, EvaluationInterfaceFactory, \
    BenchmarkFactory, ImplementationFactory


class InterfaceFactoryTest(APITestCase):
    def test_can_create(self):
        interface = EvaluationInterfaceFactory()
        eval_algorithm = AlgorithmFactory(interface=interface)
        evaluator = ImplementationFactory(algorithm=eval_algorithm)
        benchmark = BenchmarkFactory(evaluator=evaluator)
        benchmark.clean()