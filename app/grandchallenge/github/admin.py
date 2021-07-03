from django.contrib import admin

from grandchallenge.github.models import GitHubWebhookMessage


class GitHubWebhookMessageAdmin(admin.ModelAdmin):
    exclude = ("zipfile",)
    readonly_fields = ("payload",)


admin.site.register(GitHubWebhookMessage, GitHubWebhookMessageAdmin)
