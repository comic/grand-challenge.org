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
        ResultFactory(challenge=challenge, metrics={'a': 0.7}),
        ResultFactory(challenge=challenge, metrics={'a': 0.5}),
        ResultFactory(challenge=challenge, metrics={'a': 1.0}),
    )
    expected_ranks = [4, 2, 3, 1]

    # Execute calculate_ranks manually
    calculate_ranks(challenge_pk=challenge.pk)

    challenge = ComicSite.objects.get(pk=challenge.pk)
    rank = challenge.evaluation_ranks

    for q, exp in zip(queryset, expected_ranks):
        assert rank[str(q.pk)]['a'] == exp
