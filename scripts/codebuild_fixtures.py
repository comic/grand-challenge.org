from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

from django.core.files import File
from django.db.transaction import on_commit

from grandchallenge.codebuild.tasks import create_codebuild_build
from grandchallenge.github.models import GitHubWebhookMessage


def run():
    ghwm = _create_github_webhook_message()

    on_commit(
        create_codebuild_build.signature(kwargs={"pk": ghwm.pk}).apply_async
    )


def _create_github_webhook_message():
    payload = {
        "ref": "External_Reference",
        "sender": {
            "id": 12345678,
            "url": "https://api.github.com/users/github-username",
            "type": "User",
            "login": "github-username",
            "node_id": "NodeID1234567890",
            "html_url": "https://github.com/github-username",
            "gists_url": "https://api.github.com/users/github-username/gists{/gist_id}",
            "repos_url": "https://api.github.com/users/github-username/repos",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4",
            "events_url": "https://api.github.com/users/github-username/events{/privacy}",
            "site_admin": False,
            "gravatar_id": "",
            "starred_url": "https://api.github.com/users/github-username/starred{/owner}{/repo}",
            "followers_url": "https://api.github.com/users/github-username/followers",
            "following_url": "https://api.github.com/users/github-username/following{/other_user}",
            "organizations_url": "https://api.github.com/users/github-username/orgs",
            "subscriptions_url": "https://api.github.com/users/github-username/subscriptions",
            "received_events_url": "https://api.github.com/users/github-username/received_events",
        },
        "repository": {
            "id": 1234567890,
            "url": "https://api.github.com/repos/github-username/repo-name",
            "fork": False,
            "name": "repo-name",
            "size": 7,
            "forks": 0,
            "owner": {
                "id": 12345678,
                "url": "https://api.github.com/users/github-username",
                "type": "User",
                "login": "github-username",
                "node_id": "NodeID1234567890",
                "html_url": "https://github.com/github-username",
                "gists_url": "https://api.github.com/users/github-username/gists{/gist_id}",
                "repos_url": "https://api.github.com/users/github-username/repos",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4",
                "events_url": "https://api.github.com/users/github-username/events{/privacy}",
                "site_admin": False,
                "gravatar_id": "",
                "starred_url": "https://api.github.com/users/github-username/starred{/owner}{/repo}",
                "followers_url": "https://api.github.com/users/github-username/followers",
                "following_url": "https://api.github.com/users/github-username/following{/other_user}",
                "organizations_url": "https://api.github.com/users/github-username/orgs",
                "subscriptions_url": "https://api.github.com/users/github-username/subscriptions",
                "received_events_url": "https://api.github.com/users/github-username/received_events",
            },
            "topics": [],
            "git_url": "git://github.com/github-username/repo-name.git",
            "license": None,
            "node_id": "NodeID123456",
            "private": False,
            "ssh_url": "git@github.com:github-username/repo-name.git",
            "svn_url": "https://github.com/github-username/repo-name",
            "archived": False,
            "disabled": False,
            "has_wiki": True,
            "homepage": None,
            "html_url": "https://github.com/github-username/repo-name",
            "keys_url": "https://api.github.com/repos/github-username/repo-name/keys{/key_id}",
            "language": "Python",
            "tags_url": "https://api.github.com/repos/github-username/repo-name/tags",
            "watchers": 0,
            "blobs_url": "https://api.github.com/repos/github-username/repo-name/git/blobs{/sha}",
            "clone_url": "https://github.com/github-username/repo-name.git",
            "forks_url": "https://api.github.com/repos/github-username/repo-name/forks",
            "full_name": "github-username/repo-name",
            "has_pages": False,
            "hooks_url": "https://api.github.com/repos/github-username/repo-name/hooks",
            "pulls_url": "https://api.github.com/repos/github-username/repo-name/pulls{/number}",
            "pushed_at": "2024-01-27T12:32:21Z",
            "teams_url": "https://api.github.com/repos/github-username/repo-name/teams",
            "trees_url": "https://api.github.com/repos/github-username/repo-name/git/trees{/sha}",
            "created_at": "2024-01-24T07:31:55Z",
            "events_url": "https://api.github.com/repos/github-username/repo-name/events",
            "has_issues": True,
            "issues_url": "https://api.github.com/repos/github-username/repo-name/issues{/number}",
            "labels_url": "https://api.github.com/repos/github-username/repo-name/labels{/name}",
            "merges_url": "https://api.github.com/repos/github-username/repo-name/merges",
            "mirror_url": None,
            "updated_at": "2024-01-24T08:29:56Z",
            "visibility": "public",
            "archive_url": "https://api.github.com/repos/github-username/repo-name/{archive_format}{/ref}",
            "commits_url": "https://api.github.com/repos/github-username/repo-name/commits{/sha}",
            "compare_url": "https://api.github.com/repos/github-username/repo-name/compare/{base}...{head}",
            "description": "Description of the Repo",
            "forks_count": 0,
            "is_template": False,
            "open_issues": 0,
            "branches_url": "https://api.github.com/repos/github-username/repo-name/branches{/branch}",
            "comments_url": "https://api.github.com/repos/github-username/repo-name/comments{/number}",
            "contents_url": "https://api.github.com/repos/github-username/repo-name/contents/{+path}",
            "git_refs_url": "https://api.github.com/repos/github-username/repo-name/git/refs{/sha}",
            "git_tags_url": "https://api.github.com/repos/github-username/repo-name/git/tags{/sha}",
            "has_projects": True,
            "releases_url": "https://api.github.com/repos/github-username/repo-name/releases{/id}",
            "statuses_url": "https://api.github.com/repos/github-username/repo-name/statuses/{sha}",
            "allow_forking": True,
            "assignees_url": "https://api.github.com/repos/github-username/repo-name/assignees{/user}",
            "downloads_url": "https://api.github.com/repos/github-username/repo-name/downloads",
            "has_downloads": True,
            "languages_url": "https://api.github.com/repos/github-username/repo-name/languages",
            "default_branch": "main",
            "milestones_url": "https://api.github.com/repos/github-username/repo-name/milestones{/number}",
            "stargazers_url": "https://api.github.com/repos/github-username/repo-name/stargazers",
            "watchers_count": 0,
            "deployments_url": "https://api.github.com/repos/github-username/repo-name/deployments",
            "git_commits_url": "https://api.github.com/repos/github-username/repo-name/git/commits{/sha}",
            "has_discussions": False,
            "subscribers_url": "https://api.github.com/repos/github-username/repo-name/subscribers",
            "contributors_url": "https://api.github.com/repos/github-username/repo-name/contributors",
            "issue_events_url": "https://api.github.com/repos/github-username/repo-name/issues/events{/number}",
            "stargazers_count": 0,
            "subscription_url": "https://api.github.com/repos/github-username/repo-name/subscription",
            "collaborators_url": "https://api.github.com/repos/github-username/repo-name/collaborators{/collaborator}",
            "issue_comment_url": "https://api.github.com/repos/github-username/repo-name/issues/comments{/number}",
            "notifications_url": "https://api.github.com/repos/github-username/repo-name/notifications{?since,all,participating}",
            "open_issues_count": 0,
            "web_commit_signoff_required": False,
        },
        "description": "Description of the Repo",
        "pusher_type": "user",
        "installation": {
            "id": 123456789,
            "node_id": "NodeID1234567890abcdef=",
        },
        "master_branch": "main",
    }

    ghwm = GitHubWebhookMessage.objects.create(payload=payload)

    with NamedTemporaryFile() as f:
        demo_algorithm_path = (
            Path(__file__).parent.parent
            / "app"
            / "tests"
            / "resources"
            / "gc_demo_algorithm"
        )

        with ZipFile(f, "w") as z:
            for file in demo_algorithm_path.glob("*"):
                z.write(file, arcname=file.name)

        f.seek(0)

        ghwm.zipfile.save("test.zip", File(f))

    ghwm.payload["ref_type"] = "tag"
    ghwm.clone_status = GitHubWebhookMessage.CloneStatusChoices.SUCCESS
    ghwm.save()

    return ghwm
