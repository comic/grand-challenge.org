import factory

from grandchallenge.github.models import GitHubWebhookMessage

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
