import pytest

from grandchallenge.reader_studies.models import Answer
from grandchallenge.reader_studies.templatetags.reader_study_tags import (
    get_ground_truth,
)


@pytest.mark.skip
@pytest.mark.django_db
def test_get_ground_truth(reader_study_with_mc_gt):
    rs = reader_study_with_mc_gt
    for ds in rs.display_sets.all():
        for q in rs.questions.all():
            assert (
                get_ground_truth(rs, ds.pk, q.question_text)
                == Answer.objects.get(
                    question=q, display_set=ds, is_ground_truth=True
                ).answer_text
            )
