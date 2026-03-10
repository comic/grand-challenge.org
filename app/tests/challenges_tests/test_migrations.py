import importlib

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group
from guardian.shortcuts import get_group_perms, get_user_perms, remove_perm

from tests.factories import ChallengeRequestFactory

_migration = importlib.import_module(
    "grandchallenge.challenges.migrations"
    ".0070_assign_review_perm_to_reviewers_group"
)


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

    _migration.assign_review_perm_to_reviewers_group(apps, schema_editor=None)

    assert "review_challengerequest" in get_group_perms(
        reviewers_group, challenge_request
    )


@pytest.mark.django_db
def test_assign_change_perm_to_creators():
    challenge_request = ChallengeRequestFactory()

    # The permission is assigned when the object is created; remove it to
    # simulate the pre-migration state where it was missing.
    assert "change_challengerequest" in get_user_perms(
        challenge_request.creator, challenge_request
    )
    remove_perm(
        "change_challengerequest", challenge_request.creator, challenge_request
    )
    assert "change_challengerequest" not in get_user_perms(
        challenge_request.creator, challenge_request
    )

    _migration.assign_change_perm_to_creators(apps, schema_editor=None)

    assert "change_challengerequest" in get_user_perms(
        challenge_request.creator, challenge_request
    )
