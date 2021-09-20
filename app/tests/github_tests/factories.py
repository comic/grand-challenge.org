from datetime import timedelta

import factory
from django.utils import timezone

from grandchallenge.github.models import GitHubUserToken, GitHubWebhookMessage

PAYLOAD = {
    "description": None,
    "master_branch": "main",
    "pusher_type": "user",
    "ref": "v0.4.2",
    "ref_type": "tag",
    "repository": {
        "full_name": "DIAGNijmegen/rse-panimg",
        "html_url": "https://github.com/DIAGNijmegen/rse-panimg",
    },
    "sender": {},
}


class GitHubWebhookMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GitHubWebhookMessage

    payload = PAYLOAD
    zipfile = None


class GitHubUserTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GitHubUserToken

    access_token = factory.fuzzy.FuzzyText(length=10, prefix="ghu")
    access_token_expires = factory.fuzzy.FuzzyDateTime(
        timezone.now() + timedelta(hours=8),
        timezone.now() + timedelta(hours=12),
    )
    refresh_token = factory.fuzzy.FuzzyText(length=10, prefix="ghu")
    refresh_token_expires = factory.fuzzy.FuzzyDateTime(
        timezone.now() + timedelta(hours=12),
        timezone.now() + timedelta(hours=24),
    )
    github_user_id = factory.sequence(lambda n: n)
