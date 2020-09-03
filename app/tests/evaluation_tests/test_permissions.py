from django.test import TestCase
from guardian.shortcuts import get_groups_with_perms, get_users_with_perms

from grandchallenge.evaluation.models import AlgorithmEvaluation
from tests.evaluation_tests.factories import AlgorithmEvaluationFactory


class TestAlgorithmEvaluationPermissions(TestCase):
    def test_algorithm_evaluation_permissions(self):
        """
        Only the challenge admins should be able to view algorithm evaluations
        The submission creator, algorithm groups and participants should not
        have view permissions
        """
        ae: AlgorithmEvaluation = AlgorithmEvaluationFactory()

        assert get_groups_with_perms(ae, attach_perms=True) == {
            ae.submission.phase.challenge.admins_group: [
                "view_algorithmevaluation"
            ]
        }
        assert get_users_with_perms(ae, with_group_users=False).count() == 0
