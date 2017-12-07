import pytest


@pytest.mark.django_db
def test_challenge_set_fixture(ChallengeSet):
    assert ChallengeSet.challenge.is_admin(
        ChallengeSet.creator) == True
    assert ChallengeSet.challenge.is_participant(
        ChallengeSet.creator) == False

    assert ChallengeSet.challenge.is_admin(
        ChallengeSet.admin) == True
    assert ChallengeSet.challenge.is_participant(
        ChallengeSet.admin) == False

    assert ChallengeSet.challenge.is_admin(
        ChallengeSet.participant) == False
    assert ChallengeSet.challenge.is_participant(
        ChallengeSet.participant) == True

    assert ChallengeSet.challenge.is_admin(
        ChallengeSet.participant1) == False
    assert ChallengeSet.challenge.is_participant(
        ChallengeSet.participant1) == True

    assert ChallengeSet.participant != ChallengeSet.participant1

    assert ChallengeSet.challenge.is_admin(
        ChallengeSet.non_participant) == False
    assert ChallengeSet.challenge.is_participant(
        ChallengeSet.non_participant) == False


@pytest.mark.django_db
def test_eval_challenge_set_fixture(EvalChallengeSet):
    assert EvalChallengeSet.ChallengeSet.challenge.use_evaluation == True
    assert EvalChallengeSet.ChallengeSet.challenge == EvalChallengeSet.method.challenge
