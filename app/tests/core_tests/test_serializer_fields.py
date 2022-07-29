import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers

from grandchallenge.core.serializer_fields import PkToHyperlinkedRelatedField


@pytest.mark.django_db
def test_pk_to_hyperlinked_serializer():
    class TestSerializer(serializers.Serializer):
        related_user = PkToHyperlinkedRelatedField(
            queryset=get_user_model().objects.all(),
            view_name="api:profiles-user-detail",
        )

    serializer = TestSerializer(data={"related_user": -1})
    assert not serializer.is_valid()
    assert serializer.errors["related_user"] == [
        'Invalid pk "-1" - object does not exist.'
    ]

    u = get_user_model().objects.create(username="test")
    serializer = TestSerializer(data={"related_user": u.pk})
    assert serializer.is_valid()
    assert serializer.validated_data["related_user"] == u
