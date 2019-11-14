import pytest

from tests.utils import validate_admin_only_view


@pytest.mark.django_db
def test_upload_list(client, two_challenge_sets):
    reverse_kwargs = {}
    validate_admin_only_view(
        viewname="uploads:list",
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )
