import re
from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.core.fields import RegexField
from tests.reader_studies_tests.factories import QuestionFactory


class ModelWithRegex(models.Model):
    regex = RegexField()


@pytest.mark.parametrize(
    "value, error",
    (
        (
            r"[abc]",
            nullcontext(),
        ),
        (
            r"[abc",  # Missing closing bracket
            pytest.raises(ValidationError),
        ),
    ),
)
def test_regex_field_validation(value, error):
    model = ModelWithRegex(regex=value)
    with error:
        model.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "pattern, matches, does_not_matches",
    (
        (
            "foo",
            (
                "foo",
                "foobar",
                "\nbarfoo",
            ),
            (),
        ),
        (
            r"^(https?://)?([\da-z.-]+).([a-z.]{2,6})([/\w .-]*)*/?$",
            (
                "i.am.valid.org",
                "http://i.am.valid.org/",
                "https://i.am.valid.com/path1/path2",
            ),
            (
                "ttp://i.am.not.valid",
                "ttps://i.am.not.valid",
                "i.am.not.valid.o/p?param=value",
            ),
        ),
    ),
)
def test_regex_field_robustness(pattern, matches, does_not_matches):
    # This test is not as isolated as we'd like but not creating
    # a custom model / tables in the db, just for testing, saves a lot
    # on runtime of this test.

    # Sanity check on the patterns
    for m in matches:
        assert re.search(pattern, m)
    for n_m in does_not_matches:
        assert not re.search(pattern, n_m)

    qu = QuestionFactory(answer_match_pattern=pattern)

    # Sanity check on field type, since that is what we are testing
    assert type(qu._meta.get_field("answer_match_pattern")) is RegexField

    qu.refresh_from_db()  # load it back from the database

    new_pattern = qu.answer_match_pattern

    assert pattern == new_pattern

    for m in matches:
        assert re.search(new_pattern, m)
    for n_m in does_not_matches:
        assert not re.search(new_pattern, n_m)
