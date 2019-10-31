import pytest


@pytest.mark.django_db
def test_challenge_set_fixture(challenge_set):
    assert challenge_set.challenge.is_admin(challenge_set.creator)
    assert not challenge_set.challenge.is_participant(challenge_set.creator)
    assert challenge_set.challenge.is_admin(challenge_set.admin)
    assert not challenge_set.challenge.is_participant(challenge_set.admin)
    assert not challenge_set.challenge.is_admin(challenge_set.participant)
    assert challenge_set.challenge.is_participant(challenge_set.participant)
    assert not challenge_set.challenge.is_admin(challenge_set.participant1)
    assert challenge_set.challenge.is_participant(challenge_set.participant1)
    assert challenge_set.participant != challenge_set.participant1
    assert not challenge_set.challenge.is_admin(challenge_set.non_participant)
    assert not challenge_set.challenge.is_participant(
        challenge_set.non_participant
    )


@pytest.mark.django_db
def test_two_challenge_sets_fixture(two_challenge_sets):
    assert two_challenge_sets.challenge_set_1.challenge.is_admin(
        two_challenge_sets.admin12
    )
    assert two_challenge_sets.challenge_set_2.challenge.is_admin(
        two_challenge_sets.admin12
    )
    assert not two_challenge_sets.challenge_set_1.challenge.is_participant(
        two_challenge_sets.admin12
    )
    assert not two_challenge_sets.challenge_set_2.challenge.is_participant(
        two_challenge_sets.admin12
    )
    assert two_challenge_sets.challenge_set_1.challenge.is_participant(
        two_challenge_sets.participant12
    )
    assert two_challenge_sets.challenge_set_2.challenge.is_participant(
        two_challenge_sets.participant12
    )
    assert not two_challenge_sets.challenge_set_1.challenge.is_admin(
        two_challenge_sets.participant12
    )
    assert not two_challenge_sets.challenge_set_2.challenge.is_admin(
        two_challenge_sets.participant12
    )
    assert not two_challenge_sets.challenge_set_1.challenge.is_participant(
        two_challenge_sets.admin1participant2
    )
    assert two_challenge_sets.challenge_set_2.challenge.is_participant(
        two_challenge_sets.admin1participant2
    )
    assert two_challenge_sets.challenge_set_1.challenge.is_admin(
        two_challenge_sets.admin1participant2
    )
    assert not two_challenge_sets.challenge_set_2.challenge.is_admin(
        two_challenge_sets.admin1participant2
    )


@pytest.mark.django_db
def test_eval_challenge_set_fixture(eval_challenge_set):
    assert eval_challenge_set.challenge_set.challenge.use_evaluation
    assert (
        eval_challenge_set.challenge_set.challenge
        == eval_challenge_set.method.challenge
    )
