import factory
import pytest
from django.db.models import signals

from comicmodels.models import ComicSite
from evaluation.tasks import calculate_ranks
from tests.factories import ResultFactory, ChallengeFactory


@pytest.mark.django_db
@factory.django.mute_signals(signals.post_save)
def test_calculate_ranks():
    challenge = ChallengeFactory(evaluation_score_jsonpath='a')
    queryset = (
        ResultFactory(challenge=challenge, metrics={'a': 0.1}),
        ResultFactory(challenge=challenge, metrics={'a': 0.5}),
        ResultFactory(challenge=challenge, metrics={'a': 1.0}),
        ResultFactory(challenge=challenge, metrics={'a': 0.7}),
        ResultFactory(challenge=challenge, metrics={'a': 0.5}),
        ResultFactory(challenge=challenge, metrics={'a': 1.0}),
    )
    # An alternative implementation could be [4, 3, 1, 2, 3, 1] as there are
    # only 4 unique values, the current implementation is harsh on poor results
    expected_ranks = [6, 4, 1, 3, 4, 1]

    challenge = assert_ranks(challenge, expected_ranks, queryset)

    # now test reverse order
    challenge.evaluation_score_default_sort = challenge.ASCENDING
    challenge.save()

    expected_ranks = [1, 2, 5, 4, 2, 5]

    assert_ranks(challenge, expected_ranks, queryset)


def assert_ranks(challenge, expected_ranks, queryset):
    # Execute calculate_ranks manually
    calculate_ranks(challenge_pk=challenge.pk)
    challenge = ComicSite.objects.get(pk=challenge.pk)
    rank = challenge.evaluation_ranks
    for q, exp in zip(queryset, expected_ranks):
        assert rank[str(q.pk)]['a'] == exp
    return challenge
