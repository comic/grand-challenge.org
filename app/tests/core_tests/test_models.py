import pytest
from django.core.exceptions import ValidationError

from grandchallenge.core.models import TermsOfService


@pytest.mark.django_db
def test_multiple_terms():
    TermsOfService.objects.create()
    assert TermsOfService.objects.count() == 1
    with pytest.raises(ValidationError):
        TermsOfService.objects.create()
    assert TermsOfService.objects.count() == 1
