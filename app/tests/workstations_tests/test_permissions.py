import pytest
from django.conf import settings
from django.contrib.auth.models import Group


@pytest.mark.django_db
def test_workstation_creators_group_exists():
    assert Group.objects.get(name=settings.WORKSTATIONS_CREATORS_GROUP_NAME)
