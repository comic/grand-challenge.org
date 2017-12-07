from collections import namedtuple

import pytest

from tests.factories import UserFactory, ChallengeFactory, MethodFactory

""" Defines fixtures than can be used across all of the tests """


@pytest.fixture(name='ChallengeSet')
def challenge_set():
    """ Creates a challenge with creator, 2 participants, and non participant.
    To use this you must mark the test with @pytest.mark.django_db """
    ChallengeSet = namedtuple('ChallengeSet',
                              [
                                  'challenge',
                                  'creator',
                                  'admin',
                                  'participant',
                                  'participant1',
                                  'non_participant'
                              ])

    creator = UserFactory()
    challenge = ChallengeFactory(creator=creator)
    admin = UserFactory()
    challenge.add_admin(admin)
    participant = UserFactory()
    challenge.add_participant(participant)
    participant1 = UserFactory()
    challenge.add_participant(participant1)
    non_participant = UserFactory()

    return ChallengeSet(
        challenge,
        creator,
        admin,
        participant,
        participant1,
        non_participant
    )


@pytest.fixture(name='TwoChallengeSets')
def two_challenge_sets():
    """ Creates two challenges with combination participants and admins """
    TwoChallengeSets = namedtuple('TwoChallengeSets',
                                  [
                                      'ChallengeSet1',
                                      'ChallengeSet2',
                                      'admin12',
                                      'participant12',
                                      'admin1participant2'
                                  ])

    ChallengeSet1 = challenge_set()
    ChallengeSet2 = challenge_set()

    admin12 = UserFactory()
    ChallengeSet1.challenge.add_admin(admin12)
    ChallengeSet2.challenge.add_admin(admin12)

    participant12 = UserFactory()
    ChallengeSet1.challenge.add_participant(participant12)
    ChallengeSet2.challenge.add_participant(participant12)

    admin1participant2 = UserFactory()
    ChallengeSet1.challenge.add_admin(admin1participant2)
    ChallengeSet2.challenge.add_participant(admin1participant2)

    return TwoChallengeSets(
        ChallengeSet1,
        ChallengeSet2,
        admin12,
        participant12,
        admin1participant2
    )


@pytest.fixture(name='EvalChallengeSet')
def challenge_set_with_evaluation(ChallengeSet):
    """ Creates a challenge with two methods.
    To use this you must mark the test with @pytest.mark.django_db """
    EvalChallengeSet = namedtuple('EvalChallengeSet',
                                  [
                                      'ChallengeSet',
                                      'method'
                                  ])

    ChallengeSet.challenge.use_evaluation = True
    ChallengeSet.challenge.save()

    method = MethodFactory(challenge=ChallengeSet.challenge,
                           creator=ChallengeSet.creator)

    return EvalChallengeSet(
        ChallengeSet,
        method
    )
