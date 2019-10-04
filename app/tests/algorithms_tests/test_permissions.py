import pytest
from django.contrib.auth.models import Group


@pytest.mark.django_db
def test_algorithm_creators_group_can_add(settings):
    creators_group = Group.objects.get(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    )
    assert creators_group.permissions.filter(codename="add_algorithm").exists()
