import pytest
from django.contrib.auth.models import Group


@pytest.mark.django_db
def test_algorithm_creators_group_exists(settings):
    assert Group.objects.get(name=settings.ALGORITHMS_CREATORS_GROUP_NAME)
