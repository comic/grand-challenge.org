import pytest


@pytest.mark.django_db
def test_challenge_set_fixture(ChallengeSet):
    assert ChallengeSet.challenge.is_admin(ChallengeSet.creator)
    assert not ChallengeSet.challenge.is_participant(ChallengeSet.creator)
    assert ChallengeSet.challenge.is_admin(ChallengeSet.admin)
    assert not ChallengeSet.challenge.is_participant(ChallengeSet.admin)
    assert not ChallengeSet.challenge.is_admin(ChallengeSet.participant)
    assert ChallengeSet.challenge.is_participant(ChallengeSet.participant)
    assert not ChallengeSet.challenge.is_admin(ChallengeSet.participant1)
    assert ChallengeSet.challenge.is_participant(ChallengeSet.participant1)
    assert ChallengeSet.participant != ChallengeSet.participant1
    assert not ChallengeSet.challenge.is_admin(ChallengeSet.non_participant)
    assert not ChallengeSet.challenge.is_participant(
        ChallengeSet.non_participant
    )


@pytest.mark.django_db
def test_two_challenge_sets_fixture(TwoChallengeSets):
    assert TwoChallengeSets.ChallengeSet1.challenge.is_admin(
        TwoChallengeSets.admin12
    )
    assert TwoChallengeSets.ChallengeSet2.challenge.is_admin(
        TwoChallengeSets.admin12
    )
    assert not TwoChallengeSets.ChallengeSet1.challenge.is_participant(
        TwoChallengeSets.admin12
    )
    assert not TwoChallengeSets.ChallengeSet2.challenge.is_participant(
        TwoChallengeSets.admin12
    )
    assert TwoChallengeSets.ChallengeSet1.challenge.is_participant(
        TwoChallengeSets.participant12
    )
    assert TwoChallengeSets.ChallengeSet2.challenge.is_participant(
        TwoChallengeSets.participant12
    )
    assert not TwoChallengeSets.ChallengeSet1.challenge.is_admin(
        TwoChallengeSets.participant12
    )
    assert not TwoChallengeSets.ChallengeSet2.challenge.is_admin(
        TwoChallengeSets.participant12
    )
    assert not TwoChallengeSets.ChallengeSet1.challenge.is_participant(
        TwoChallengeSets.admin1participant2
    )
    assert TwoChallengeSets.ChallengeSet2.challenge.is_participant(
        TwoChallengeSets.admin1participant2
    )
    assert TwoChallengeSets.ChallengeSet1.challenge.is_admin(
        TwoChallengeSets.admin1participant2
    )
    assert not TwoChallengeSets.ChallengeSet2.challenge.is_admin(
        TwoChallengeSets.admin1participant2
    )


@pytest.mark.django_db
def test_eval_challenge_set_fixture(EvalChallengeSet):
    assert EvalChallengeSet.ChallengeSet.challenge.use_evaluation
    assert EvalChallengeSet.ChallengeSet.challenge == EvalChallengeSet.method.challenge
