from dataclasses import asdict, dataclass
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner


@dataclass
class GitHubState:
    redirect_url: str


def encode_github_state(*, redirect_url):
    state = GitHubState(redirect_url=redirect_url)
    return TimestampSigner().sign_object(asdict(state))


def decode_github_state(*, state):
    try:
        obj = TimestampSigner().unsign_object(
            state, max_age=timedelta(minutes=10)
        )
        return GitHubState(**obj)
    except (SignatureExpired, BadSignature):
        raise PermissionDenied
