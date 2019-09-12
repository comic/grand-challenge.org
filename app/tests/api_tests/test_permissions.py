from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from guardian.shortcuts import assign_perm

from django.conf import settings

from tests.factories import BenchmarkFactory


class AnonymousUserTest(APITestCase):
    def test_anonymous_user_exists(self):
        # should be created by guardian
        anon_user = User.objects.get(username=settings.ANONYMOUS_USER_NAME)

    def test_anon_list_benchmarks_gives_200(self):
        url = '/api/v1/benchmarks/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)

    def test_anon_get_benchmark_gives_200(self):
        benchmark = BenchmarkFactory()
        url = f'/api/v1/benchmarks/{benchmark.pk}/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)

    def test_anon_get_benchmark_model_permission_gives_200(self):
        benchmark = BenchmarkFactory()
        anon_user=User.get_anonymous()
        assign_perm('eyra_benchmarks.view_benchmark', anon_user)
        url = f'/api/v1/benchmarks/{benchmark.pk}/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)

    def test_anon_get_benchmark_object_permission_gives_200(self):
        benchmark = BenchmarkFactory()
        anon_user=User.get_anonymous()
        assign_perm('eyra_benchmarks.view_benchmark', anon_user, benchmark)
        url = f'/api/v1/benchmarks/{benchmark.pk}/'
        response = self.client.get(url, format="json")
        self.assertEqual(200, response.status_code)