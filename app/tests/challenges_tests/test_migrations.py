import importlib

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_group_perms, remove_perm

from tests.factories import ChallengeRequestFactory


@pytest.mark.django_db
def test_assign_review_perm_to_reviewers_group():
    challenge_request = ChallengeRequestFactory()
    reviewers_group = Group.objects.get(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    )

    # The permission is assigned when the object is created; remove it to
    # simulate the pre-migration state where it was missing.
    assert "review_challengerequest" in get_group_perms(
        reviewers_group, challenge_request
    )
    remove_perm("review_challengerequest", reviewers_group, challenge_request)
    assert "review_challengerequest" not in get_group_perms(
        reviewers_group, challenge_request
    )

    migration = importlib.import_module(
        "grandchallenge.challenges.migrations"
        ".0070_assign_review_perm_to_reviewers_group"
    )
    migration.assign_review_perm_to_reviewers_group(apps, schema_editor=None)

    assert "review_challengerequest" in get_group_perms(
        reviewers_group, challenge_request
    )
