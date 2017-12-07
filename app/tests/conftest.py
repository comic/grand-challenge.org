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
