import pytest

from grandchallenge.reader_studies.models import Answer
from grandchallenge.reader_studies.templatetags.get_ground_truth import (
    get_ground_truth,
)


@pytest.mark.django_db
def test_get_ground_truth(reader_study_with_mc_gt):
    rs = reader_study_with_mc_gt
    for im in rs.images.all():
        for q in rs.questions.all():
            assert (
                get_ground_truth(rs, im.name, q.question_text)
                == Answer.objects.get(
                    question=q, images=im, is_ground_truth=True
                ).answer_text
            )
