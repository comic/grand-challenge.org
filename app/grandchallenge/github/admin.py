from django.contrib import admin

from grandchallenge.github.models import GitHubWebhookMessage


admin.site.register(GitHubWebhookMessage)
