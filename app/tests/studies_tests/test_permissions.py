import pytest

from tests.studies_tests import StudyFactory
from tests.utils import validate_staff_only_view

"""" Tests the permission access for Patient Forms """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "studies:study-create",
        "studies:study-remove",
        "studies:study-update",
        "studies:study-display",
    ],
)
def test_study_form_access(view, client):
    reverse_kwargs = {}
    if view in ("studies:study-update", "studies:study-remove"):
        study = StudyFactory()
        reverse_kwargs.update({"pk": study.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )
